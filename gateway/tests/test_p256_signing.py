"""Additive ECDSA P-256 (secp256r1) device-signing support for the mobile_signed channel.

These tests mirror the Ed25519 conftest helpers for a Secure-Enclave-class P-256 key:
public key = X9.63 uncompressed point (0x04 || X || Y); signature = DER ECDSA over SHA-256;
both base64url no-pad. The canonical signing string is unchanged from HMCP-SIGN-V1. They prove
the additive path works end-to-end without disturbing the Ed25519 path.
"""

from __future__ import annotations

import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from conftest import b64url, pair_device
from hermes_gateway.signing import canonical_request


def _p256_keypair() -> tuple[ec.EllipticCurvePrivateKey, bytes]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_point = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return private_key, public_point


def _p256_sign(private_key: ec.EllipticCurvePrivateKey, message: bytes) -> str:
    return b64url(private_key.sign(message, ec.ECDSA(hashes.SHA256())))


def pair_p256_device(
    client: TestClient,
    *,
    with_proof: bool = True,
    proof_message: bytes | None = None,
    clearance_channel: str = "mobile_signed",
) -> tuple[ec.EllipticCurvePrivateKey, dict, object]:
    private_key, public_point = _p256_keypair()
    start = client.post(
        "/v1/pairing/start",
        json={
            "display_name": "Enclave Phone",
            "requested_permissions": ["read_state", "approve", "intervene"],
            "clearance_channel": clearance_channel,
        },
    )
    assert start.status_code == 201
    pairing = start.json()
    body: dict = {
        "pairing_id": pairing["pairing_id"],
        "challenge_response": pairing["pairing_token"],
        "device_public_key": b64url(public_point),
        "device": {
            "device_name": "Enclave Phone",
            "platform": "ios",
            "app_instance_id": "app-enclave-1",
            "app_version": "0.2.0",
        },
        "device_key_algorithm": "p256",
    }
    if with_proof:
        message = (
            proof_message
            if proof_message is not None
            else pairing["challenge"].encode("utf-8")
        )
        body["device_key_possession_proof"] = _p256_sign(private_key, message)
    complete = client.post("/v1/pairing/complete", json=body)
    return private_key, pairing, complete


def _p256_headers(
    private_key: ec.EllipticCurvePrivateKey,
    device_id: str,
    method: str,
    path: str,
    body: bytes = b"",
) -> dict[str, str]:
    timestamp = str(int(time.time()))
    nonce = f"nonce-{time.time_ns()}"
    canonical = canonical_request(
        method=method, path=path, timestamp=timestamp, nonce=nonce, body=body
    )
    return {
        "X-HMCP-Device-Id": device_id,
        "X-HMCP-Timestamp": timestamp,
        "X-HMCP-Nonce": nonce,
        "X-HMCP-Signature": _p256_sign(private_key, canonical.encode("utf-8")),
    }


def test_p256_pairing_with_possession_proof_succeeds(client: TestClient) -> None:
    _private_key, _pairing, complete = pair_p256_device(client)
    assert complete.status_code == 200
    device = complete.json()["device"]
    assert device["device_key_algorithm"] == "p256"
    assert device["clearance_channel"] == "mobile_signed"


def test_p256_signed_request_is_accepted(client: TestClient) -> None:
    private_key, _pairing, complete = pair_p256_device(client)
    device_id = complete.json()["device"]["device_id"]
    headers = _p256_headers(private_key, device_id, "GET", "/v1/devices")
    response = client.get("/v1/devices", headers=headers)
    assert response.status_code == 200
    device_ids = {d["device_id"] for d in response.json()["devices"]}
    assert device_id in device_ids


def test_p256_tampered_signature_is_rejected(client: TestClient) -> None:
    private_key, _pairing, complete = pair_p256_device(client)
    device_id = complete.json()["device"]["device_id"]
    headers = _p256_headers(private_key, device_id, "GET", "/v1/devices")
    # Flip the signature to a different valid-shaped P-256 signature -> must fail closed.
    other_key, _ = _p256_keypair()
    headers["X-HMCP-Signature"] = _p256_sign(other_key, b"unrelated")
    response = client.get("/v1/devices", headers=headers)
    assert response.status_code == 401


def test_p256_requires_possession_proof(client: TestClient) -> None:
    _private_key, _pairing, complete = pair_p256_device(client, with_proof=False)
    assert complete.status_code == 400
    assert "possession proof" in complete.json()["detail"].lower()


def test_p256_invalid_possession_proof_is_rejected(client: TestClient) -> None:
    # Sign the WRONG message (not the challenge) -> possession proof must be rejected.
    _private_key, _pairing, complete = pair_p256_device(
        client, proof_message=b"not-the-challenge"
    )
    assert complete.status_code == 400
    assert "possession proof" in complete.json()["detail"].lower()


def test_unsupported_key_algorithm_is_rejected(client: TestClient) -> None:
    start = client.post(
        "/v1/pairing/start",
        json={"display_name": "Bad Phone", "clearance_channel": "mobile_signed"},
    )
    pairing = start.json()
    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": b64url(b"\x04" + b"\x00" * 64),
            "device": {
                "device_name": "Bad Phone",
                "platform": "ios",
                "app_instance_id": "app-bad-1",
            },
            "device_key_algorithm": "rsa",
        },
    )
    assert complete.status_code == 400
    assert "algorithm" in complete.json()["detail"].lower()


def test_ed25519_pairing_still_defaults_and_works(client: TestClient) -> None:
    # The legacy Ed25519 path is unchanged: no algorithm field -> defaults to ed25519.
    paired = pair_device(client, clearance_channel="mobile_signed")
    assert paired["device"]["device_key_algorithm"] == "ed25519"
