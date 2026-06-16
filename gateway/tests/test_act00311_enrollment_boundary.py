from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from conftest import b64url, pair_device, signed_request


def test_pairing_completion_cannot_self_declare_mobile_channel(
    client: TestClient,
) -> None:
    start = client.post(
        "/v1/pairing/start",
        json={"display_name": "Terminal Enrollment"},
    )
    assert start.status_code == 201
    pairing = start.json()

    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": "pubkey-self-upgrade",
            "device": {
                "device_name": "Self Upgrader",
                "platform": "ios",
                "app_instance_id": "app-self-upgrade",
                "clearance_channel": "mobile_signed",
            },
        },
    )

    assert complete.status_code == 400
    assert complete.json()["detail"] == "device clearance channel mismatch"
    audit_events = client.app.state.store.list_audit_events(event_type="pairing_rejected")
    assert audit_events
    payload = audit_events[0]["payload_redacted"]
    assert payload["reason"] == "device_clearance_channel_conflict"
    assert payload["session_clearance_channel"] == "local_terminal"
    assert payload["device_clearance_channel"] == "mobile_signed"


def test_pairing_completion_uses_operator_pinned_mobile_channel(
    client: TestClient,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    start = client.post(
        "/v1/pairing/start",
        json={
            "display_name": "Owner Phone",
            "requested_permissions": ["read_state", "approve"],
            "clearance_channel": "mobile_signed",
        },
    )
    assert start.status_code == 201
    pairing = start.json()
    assert pairing["clearance_channel"] == "mobile_signed"

    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": b64url(
                private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            ),
            "device": {
                "device_name": "Owner Phone",
                "platform": "ios",
                "app_instance_id": "app-owner-phone",
            },
        },
    )

    assert complete.status_code == 200
    assert complete.json()["device"]["clearance_channel"] == "mobile_signed"


def test_create_device_defaults_to_local_terminal(client: TestClient) -> None:
    device = client.app.state.store.create_device(
        node_id="node_test",
        device_name="Unspecified Principal",
        platform="local_terminal",
        app_instance_id="app-unspecified",
        app_version="0.1.0",
        device_public_key="pubkey-unspecified",
        permissions=["read_state", "approve"],
    )

    assert device["clearance_channel"] == "local_terminal"


def test_existing_mobile_class_device_still_authenticates_and_clears(
    client: TestClient,
) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "approve"])
    approval = _create_approval(client)

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert paired["device"]["clearance_channel"] == "mobile_signed"
    assert response.status_code == 200


def test_freshly_paired_local_class_principal_cannot_clear_high_risk(
    client: TestClient,
) -> None:
    paired = pair_device(
        client,
        requested_permissions=["read_state", "approve"],
        clearance_channel="local_terminal",
    )
    approval = _create_approval(client)

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert paired["device"]["clearance_channel"] == "local_terminal"
    assert response.status_code == 403


def _create_approval(client: TestClient) -> dict:
    response = client.post(
        "/v1/approvals",
        json={
            "action_id": "act_enrollment_boundary",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "requested_tool": "shell",
            "risk_level": "high",
            "risk_family": "destructive",
            "summary": "Run a high-risk command.",
            "full_payload_redacted": {"command": "redacted"},
            "expires_at": "2099-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201
    return response.json()
