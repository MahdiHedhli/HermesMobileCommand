from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hermes_gateway.app import create_app
from hermes_gateway.config import Settings


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
            "device_public_key": "test-device-public-key",
            "device": {
                "device_name": "Test Phone",
                "platform": "ios",
                "app_instance_id": "app-test-1",
                "app_version": "0.1.0",
            },
        },
    )
    assert complete.status_code == 200
    return complete.json()
