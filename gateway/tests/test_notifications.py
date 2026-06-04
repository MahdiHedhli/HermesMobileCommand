from __future__ import annotations

from fastapi.testclient import TestClient


def test_mobile_notify_creates_notification_and_audit_event(client: TestClient) -> None:
    response = client.post(
        "/v1/notifications/mobile_notify",
        json={
            "title": "Approval required",
            "body": "Hermes needs a decision for a shell command.",
            "urgency": "high",
            "category": "approval_required",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "action_id": "act_1",
        },
    )

    assert response.status_code == 202
    notification = response.json()
    assert notification["state"] == "queued"
    assert notification["category"] == "approval_required"

    audit = client.get("/v1/audit/events", params={"event_type": "notification_queued"})
    assert audit.status_code == 200
    audit_events = audit.json()["audit_events"]
    assert audit_events
    assert audit_events[0]["notification_id"] == notification["notification_id"]

    events = client.get("/v1/events")
    assert events.status_code == 200
    assert any(event["type"] == "notification.created" for event in events.json()["events"])


def test_mobile_notify_rejects_secret_like_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/notifications/mobile_notify",
        json={
            "title": "Token leaked",
            "body": "token=abc123",
            "urgency": "critical",
            "category": "security_alert",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
        },
    )

    assert response.status_code == 422
    audit = client.get("/v1/audit/events", params={"event_type": "notification_rejected"})
    assert audit.status_code == 200
    assert audit.json()["audit_events"]
