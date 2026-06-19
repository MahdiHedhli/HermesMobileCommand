"""Unit tests for APNs push dispatch (no network) — JWT + hint-only payload."""

from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from hermes_gateway.config import Settings
from hermes_gateway.push import ApnsPushDispatcher


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _write_p8(tmp_path) -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path = tmp_path / "AuthKey_TEST.p8"
    path.write_bytes(pem)
    return str(path)


def test_push_unconfigured_is_unavailable():
    dispatcher = ApnsPushDispatcher(Settings())
    assert dispatcher.configured is False
    # Dispatch is a safe no-op when unconfigured.
    dispatcher.dispatch_clearance(
        ["tok"], title="t", body="b", approval_id="a", short_code="s"
    )


def test_provider_jwt_is_well_formed_es256(tmp_path):
    key_path = _write_p8(tmp_path)
    settings = Settings(
        apns_key_path=key_path,
        apns_key_id="ABC123KEYID",
        apns_team_id="TEAM123456",
    )
    dispatcher = ApnsPushDispatcher(settings)
    assert dispatcher.configured is True

    token = dispatcher._provider_token()
    header_b64, claims_b64, sig_b64 = token.split(".")
    header = json.loads(_b64url_decode(header_b64))
    claims = json.loads(_b64url_decode(claims_b64))
    assert header == {"alg": "ES256", "kid": "ABC123KEYID"}
    assert claims["iss"] == "TEAM123456"
    assert isinstance(claims["iat"], int)

    # The signature verifies against the key's public half.
    public_key = serialization.load_pem_private_key(
        open(key_path, "rb").read(), password=None
    ).public_key()
    raw = _b64url_decode(sig_b64)
    r = int.from_bytes(raw[:32], "big")
    s = int.from_bytes(raw[32:], "big")
    from cryptography.hazmat.primitives import hashes

    public_key.verify(
        encode_dss_signature(r, s),
        f"{header_b64}.{claims_b64}".encode("ascii"),
        ec.ECDSA(hashes.SHA256()),
    )

    # Token is cached (same value within the TTL).
    assert dispatcher._provider_token() == token


def test_payload_is_hint_only_no_secrets():
    payload = ApnsPushDispatcher.build_payload(
        title="Clearance required",
        body="An agent needs your approval · external_effect · ABC123",
        approval_id="appr_1",
        short_code="ABC123",
    )
    assert payload["aps"]["alert"]["title"] == "Clearance required"
    assert payload["approval_id"] == "appr_1"
    assert payload["short_code"] == "ABC123"
    # Hint-only: no raw payload / aircraft text fields leak through.
    blob = json.dumps(payload)
    assert "payload_redacted" not in blob
    assert "operator_message" not in blob
