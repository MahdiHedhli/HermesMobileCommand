from __future__ import annotations

import base64
import json
import sys
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hermes_gateway.app import create_app
from hermes_gateway.config import Settings
from hermes_gateway.signing import canonical_request


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    settings = Settings(
        node_id="node_test",
        node_display_name="Test Hermes",
        node_fingerprint="test-fingerprint",
        gateway_base_url="http://127.0.0.1:8787/v1",
        database_path=str(tmp_path / "gateway.sqlite3"),
        pairing_ttl_seconds=60,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def pair_device(client: TestClient) -> dict:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    start = client.post(
        "/v1/pairing/start",
        json={
            "display_name": "Test Phone",
            "requested_permissions": ["read_state", "approve", "intervene"],
        },
    )
    assert start.status_code == 201
    pairing = start.json()
    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": b64url(public_key),
            "device": {
                "device_name": "Test Phone",
                "platform": "ios",
                "app_instance_id": "app-test-1",
                "app_version": "0.1.0",
            },
        },
    )
    assert complete.status_code == 200
    paired = complete.json()
    paired["private_key"] = private_key
    return paired


def signed_request(
    client: TestClient,
    method: str,
    path: str,
    *,
    private_key: Ed25519PrivateKey,
    device_id: str,
    json_body: dict[str, Any] | None = None,
    send_body: bytes | None = None,
    sign_body: bytes | None = None,
    sign_method: str | None = None,
    sign_path: str | None = None,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> Any:
    body = _json_bytes(json_body) if json_body is not None else b""
    body_to_send = send_body if send_body is not None else body
    body_to_sign = sign_body if sign_body is not None else body_to_send
    headers = signature_headers(
        private_key=private_key,
        device_id=device_id,
        method=sign_method or method,
        path=sign_path or path,
        body=body_to_sign,
        timestamp=timestamp,
        nonce=nonce,
    )
    if json_body is not None or send_body is not None:
        headers["Content-Type"] = "application/json"
    return client.request(method, path, content=body_to_send, headers=headers)


def signature_headers(
    *,
    private_key: Ed25519PrivateKey,
    device_id: str,
    method: str,
    path: str,
    body: bytes = b"",
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    timestamp_text = str(timestamp if timestamp is not None else int(time.time()))
    nonce_text = nonce or f"nonce-{time.time_ns()}"
    canonical = canonical_request(
        method=method,
        path=path,
        timestamp=timestamp_text,
        nonce=nonce_text,
        body=body,
    )
    signature = private_key.sign(canonical.encode("utf-8"))
    return {
        "X-HMCP-Device-Id": device_id,
        "X-HMCP-Timestamp": timestamp_text,
        "X-HMCP-Nonce": nonce_text,
        "X-HMCP-Signature": b64url(signature),
    }


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
