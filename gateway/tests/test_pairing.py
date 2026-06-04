from __future__ import annotations

from fastapi.testclient import TestClient


def test_device_can_register(client: TestClient) -> None:
    start = client.post(
        "/v1/pairing/start",
        json={"display_name": "Owner Phone", "requested_permissions": ["read_state", "approve"]},
    )
    assert start.status_code == 201
    pairing = start.json()
    assert pairing["status"] == "pending"
    assert pairing["pairing_token"]

    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": "pubkey-owner-phone",
            "device": {
                "device_name": "Owner Phone",
                "platform": "android",
                "app_instance_id": "app-owner-phone",
            },
        },
    )

    assert complete.status_code == 200
    body = complete.json()
    assert body["node"]["node_id"] == "node_test"
    assert body["device"]["status"] == "active"
    assert body["tokens"]["access_token"]


def test_pairing_token_expires(client: TestClient) -> None:
    start = client.post(
        "/v1/pairing/start",
        json={"display_name": "Expired Phone", "ttl_seconds": -1},
    )
    assert start.status_code == 201
    pairing = start.json()

    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": "pubkey-expired",
            "device": {
                "device_name": "Expired Phone",
                "platform": "ios",
                "app_instance_id": "app-expired",
            },
        },
    )

    assert complete.status_code == 400
    assert "expired" in complete.json()["detail"]


def test_invalid_pairing_token_rejected(client: TestClient) -> None:
    start = client.post("/v1/pairing/start", json={"display_name": "Bad Phone"})
    assert start.status_code == 201
    pairing = start.json()

    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": "wrong-token",
            "device_public_key": "pubkey-bad",
            "device": {
                "device_name": "Bad Phone",
                "platform": "ios",
                "app_instance_id": "app-bad",
            },
        },
    )

    assert complete.status_code == 400
    assert complete.json()["detail"] == "invalid pairing token"
