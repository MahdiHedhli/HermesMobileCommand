from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request


def test_hermes_tool_mobile_notify_creates_notification_audit_and_event(
    client: TestClient,
) -> None:
    paired = pair_device(client)

    response = client.post(
        "/v1/hermes/tools/mobile_notify",
        json={
            "title": "Approval required",
            "body": "Hermes needs a decision for a shell command.",
            "urgency": "high",
            "category": "approval_required",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "action_id": "act_notify_adapter",
        },
    )

    assert response.status_code == 202
    notification = response.json()
    assert notification["state"] == "queued"

    audit = signed_request(
        client,
        "GET",
        "/v1/audit/events?event_type=notification_queued",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert audit.status_code == 200
    assert audit.json()["audit_events"][0]["notification_id"] == notification["notification_id"]

    events = signed_request(
        client,
        "GET",
        "/v1/events",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert events.status_code == 200
    assert any(
        event["type"] == "notification.created"
        and event["payload"].get("notification_id") == notification["notification_id"]
        for event in events.json()["events"]
    )


def test_hermes_tool_mobile_notify_rejects_oversized_body(client: TestClient) -> None:
    response = client.post(
        "/v1/hermes/tools/mobile_notify",
        json={
            "title": "Long body",
            "body": "x" * 801,
            "urgency": "normal",
            "category": "system_health",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
        },
    )

    assert response.status_code == 422


def test_hermes_tool_mobile_notify_rejects_secret_looking_body(client: TestClient) -> None:
    response = client.post(
        "/v1/hermes/tools/mobile_notify",
        json={
            "title": "Credential found",
            "body": "api_key=abc123",
            "urgency": "critical",
            "category": "security_alert",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
        },
    )

    assert response.status_code == 422


def test_hermes_tool_approval_requested_creates_pending_approval_audit_and_event(
    client: TestClient,
) -> None:
    paired = pair_device(client)

    response = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "shell",
            "risk_level": "high",
            "summary": "Run a redacted shell command.",
            "payload_redacted": {"command": "rm -rf ./dist"},
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "expires_in_seconds": 300,
            "suggested_scopes": ["once", "session"],
            "action_id": "act_adapter_approval",
        },
    )

    assert response.status_code == 201
    approval = response.json()
    assert approval["state"] == "pending"
    assert approval["options"] == ["approve_once", "approve_for_session", "deny"]

    audit = signed_request(
        client,
        "GET",
        "/v1/audit/events?event_type=approval_requested",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert audit.status_code == 200
    assert audit.json()["audit_events"][0]["approval_id"] == approval["approval_id"]

    events = signed_request(
        client,
        "GET",
        "/v1/events",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert events.status_code == 200
    assert any(
        event["type"] == "approval.requested"
        and event["payload"].get("approval_id") == approval["approval_id"]
        for event in events.json()["events"]
    )


def test_hermes_tool_approval_status_returns_state_and_selected_scope(
    client: TestClient,
) -> None:
    paired = pair_device(client)
    approval = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "shell",
            "risk_level": "high",
            "summary": "Run a redacted shell command.",
            "payload_redacted": {"command": "redacted"},
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "expires_in_seconds": 300,
        },
    ).json()

    approved = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert approved.status_code == 200

    status = client.post(
        "/v1/hermes/tools/approval_status",
        json={"approval_id": approval["approval_id"]},
    )

    assert status.status_code == 200
    assert status.json()["state"] == "approved"
    assert status.json()["selected_scope"] == "once"


def test_hermes_tool_approval_status_rejects_unknown_approval(client: TestClient) -> None:
    response = client.post(
        "/v1/hermes/tools/approval_status",
        json={"approval_id": "appr_missing"},
    )

    assert response.status_code == 404
