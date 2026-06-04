from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device


def test_websocket_receives_mock_events(client: TestClient) -> None:
    paired = pair_device(client)
    token = paired["tokens"]["access_token"]

    with client.websocket_connect(f"/v1/events/stream?access_token={token}") as websocket:
        events = [websocket.receive_json() for _ in range(6)]

    event_types = {event["type"] for event in events}
    assert {
        "agent.status",
        "agent.activity",
        "approval.requested",
        "approval.resolved",
        "notification.created",
        "system.health",
    }.issubset(event_types)


def test_websocket_disconnect_reconnect_uses_cursor(client: TestClient) -> None:
    paired = pair_device(client)
    token = paired["tokens"]["access_token"]

    with client.websocket_connect(f"/v1/events/stream?access_token={token}") as websocket:
        first = websocket.receive_json()
        cursor = first["cursor"]

    with client.websocket_connect(
        f"/v1/events/stream?access_token={token}&after={cursor}"
    ) as websocket:
        resumed = websocket.receive_json()

    assert resumed["cursor"] != cursor
    assert resumed["type"] in {
        "agent.activity",
        "approval.requested",
        "approval.resolved",
        "notification.created",
        "system.health",
    }
