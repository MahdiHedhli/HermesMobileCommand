from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request


def test_create_and_list_pending_approval(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(client, action_id="act_create")

    response = signed_request(
        client,
        "GET",
        "/v1/approvals?state=pending",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    approvals = response.json()["approvals"]
    assert any(item["approval_id"] == approval["approval_id"] for item in approvals)


def test_approve_once_creates_audit_and_event(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(client, action_id="act_approve")

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    assert response.json()["state"] == "approved"
    assert response.json()["applied_scope"] == "once"
    assert audit_exists(client, paired, "approval_decision")
    assert approval_event_exists(client, approval["approval_id"], "approved")


def test_deny_approval(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(client, action_id="act_deny")

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/deny",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    assert response.json()["state"] == "denied"


def test_expire_approval(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(client, action_id="act_expire")

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/expire",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    assert response.json()["state"] == "expired"


def test_cancel_approval(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(client, action_id="act_cancel")

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/cancel",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    assert response.json()["state"] == "cancelled"


def test_invalid_transition_rejected(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(client, action_id="act_transition")
    first = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert first.status_code == 200

    second = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/deny",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "approval is not pending"


def test_expired_approval_cannot_be_approved(client: TestClient) -> None:
    paired = pair_device(client)
    approval = create_approval(
        client,
        action_id="act_expired",
        expires_at="2000-01-01T00:00:00Z",
    )

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "approval expired"
    assert approval_event_exists(client, approval["approval_id"], "expired")


def test_invalid_approval_id_rejected(client: TestClient) -> None:
    paired = pair_device(client)

    response = signed_request(
        client,
        "POST",
        "/v1/approvals/appr_missing/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 404


def create_approval(
    client: TestClient,
    *,
    action_id: str,
    expires_at: str = "2099-01-01T00:00:00Z",
) -> dict:
    response = client.post(
        "/v1/approvals",
        json={
            "action_id": action_id,
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "requested_tool": "shell",
            "risk_level": "high",
            "summary": "Run a command",
            "full_payload_redacted": {"command": "redacted"},
            "resource_scope": "repo",
            "expires_at": expires_at,
        },
    )
    assert response.status_code == 201
    return response.json()


def audit_exists(client: TestClient, paired: dict, event_type: str) -> bool:
    response = signed_request(
        client,
        "GET",
        f"/v1/audit/events?event_type={event_type}",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert response.status_code == 200
    return bool(response.json()["audit_events"])


def approval_event_exists(client: TestClient, approval_id: str, state: str) -> bool:
    response = client.get("/v1/events")
    assert response.status_code == 200
    return any(
        event["type"] == "approval.resolved"
        and event["payload"].get("approval_id") == approval_id
        and event["payload"].get("state") == state
        for event in response.json()["events"]
    )
