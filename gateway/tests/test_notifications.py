from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request


def test_mobile_notify_creates_notification_and_audit_event(client: TestClient) -> None:
    paired = pair_device(client)
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
    assert notification["title_safe"] == "Clearance required"
    assert "shell command" not in notification["body_safe"]
    assert notification["composition_mode"] == "template_allowlist"

    audit = signed_request(
        client,
        "GET",
        "/v1/audit/events?event_type=notification_queued",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert audit.status_code == 200
    audit_events = audit.json()["audit_events"]
    assert audit_events
    assert audit_events[0]["notification_id"] == notification["notification_id"]

    events = signed_request(
        client,
        "GET",
        "/v1/events",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert events.status_code == 200
    assert any(event["type"] == "notification.created" for event in events.json()["events"])


def test_mobile_notify_sanitizes_secret_like_payload(client: TestClient) -> None:
    paired = pair_device(client)
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

    assert response.status_code == 202
    notification = response.json()
    assert notification["title_safe"] == "Security alert"
    assert "abc123" not in notification["body_safe"]
    assert notification["composition_mode"] == "template_sanitized"
    assert notification["unsafe_input_detected"] is True
    audit = signed_request(
        client,
        "GET",
        "/v1/audit/events?event_type=notification_queued",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert audit.status_code == 200
    audit_events = audit.json()["audit_events"]
    assert audit_events
    payload = audit_events[0]["payload_redacted"]
    assert payload["unsafe_input_detected"] is True
    assert "secret_marker_detected" in payload["unsafe_reasons"]
    assert "abc123" not in str(payload)
    assert "token=abc123" not in str(payload)


def test_mobile_notify_rejects_raw_preview_echo_with_high_entropy_backstop(
    client: TestClient,
) -> None:
    paired = pair_device(client)
    response = client.post(
        "/v1/notifications/mobile_notify",
        json={
            "title": "Submit token",
            "body": "Use AKIAIOSFODNN7EXAMPLEsecretpayload0987654321",
            "urgency": "critical",
            "category": "approval_required",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "risk_family": "external_effect",
            "operation_label": "live form submission",
        },
    )

    assert response.status_code == 202
    notification = response.json()
    assert notification["title_safe"] == "Clearance required"
    assert "AKIA" not in notification["body_safe"]
    assert "live form submission" in notification["body_safe"]
    assert notification["unsafe_input_detected"] is True
    audit = signed_request(
        client,
        "GET",
        "/v1/audit/events?event_type=notification_queued",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert audit.status_code == 200
    payload = audit.json()["audit_events"][0]["payload_redacted"]
    assert "AKIAIOSFODNN7EXAMPLEsecretpayload0987654321" not in str(payload)
    assert "high_entropy_text_detected" in payload["unsafe_reasons"]
