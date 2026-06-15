from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request


def test_mobile_can_read_inventory_agents_notifications_and_approvals(
    client: TestClient,
) -> None:
    paired = pair_device(client)
    device_id = paired["device"]["device_id"]
    private_key = paired["private_key"]
    notification = client.post(
        "/v1/hermes/tools/mobile_notify",
        json={
            "title": "Task complete",
            "body": "Long-running task finished.",
            "urgency": "normal",
            "category": "task_complete",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
        },
    )
    assert notification.status_code == 202
    approval = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "shell",
            "risk_level": "medium",
            "risk_family": "routine",
            "summary": "Run a redacted shell command.",
            "payload_redacted": {"command": "redacted"},
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "expires_in_seconds": 300,
        },
    )
    assert approval.status_code == 201

    inventory = signed_request(
        client,
        "GET",
        "/v1/inventory",
        private_key=private_key,
        device_id=device_id,
    )
    agents = signed_request(
        client,
        "GET",
        "/v1/agents",
        private_key=private_key,
        device_id=device_id,
    )
    agent_detail = signed_request(
        client,
        "GET",
        "/v1/agents/agent_mock?node_id=node_test",
        private_key=private_key,
        device_id=device_id,
    )
    notifications = signed_request(
        client,
        "GET",
        "/v1/notifications",
        private_key=private_key,
        device_id=device_id,
    )
    approvals = signed_request(
        client,
        "GET",
        "/v1/approvals?state=pending",
        private_key=private_key,
        device_id=device_id,
    )
    approval_detail = signed_request(
        client,
        "GET",
        f"/v1/approvals/{approval.json()['approval_id']}",
        private_key=private_key,
        device_id=device_id,
    )

    assert inventory.status_code == 200
    assert agents.status_code == 200
    assert agent_detail.status_code == 200
    assert notifications.status_code == 200
    assert approvals.status_code == 200
    assert approval_detail.status_code == 200
    assert inventory.json()["nodes"]
    assert agents.json()["agents"]
    assert notifications.json()["notifications"]
    assert approvals.json()["approvals"]
    assert approval_detail.json()["approval_id"] == approval.json()["approval_id"]


def test_signed_deny_still_works_for_hermes_created_approval(client: TestClient) -> None:
    paired = pair_device(client)
    approval = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "shell",
            "risk_level": "medium",
            "risk_family": "routine",
            "summary": "Run a redacted shell command.",
            "payload_redacted": {"command": "redacted"},
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "expires_in_seconds": 300,
        },
    ).json()

    response = signed_request(
        client,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/deny",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    assert response.json()["state"] == "denied"


def test_websocket_receives_hermes_created_events(client: TestClient) -> None:
    paired = pair_device(client)
    token = paired["tokens"]["access_token"]
    approval = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "shell",
            "risk_level": "critical",
            "risk_family": "safety_critical",
            "summary": "Run a redacted shell command.",
            "payload_redacted": {"command": "redacted"},
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "expires_in_seconds": 300,
        },
    ).json()

    with client.websocket_connect(f"/v1/events/stream?access_token={token}") as websocket:
        events = [websocket.receive_json() for _ in range(9)]

    assert any(
        event["type"] == "approval.requested"
        and event["payload"].get("approval_id") == approval["approval_id"]
        for event in events
    )
