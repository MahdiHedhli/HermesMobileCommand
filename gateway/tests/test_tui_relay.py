"""TUI mirror relay: the plugin feeds the agent's terminal output (hermes-local)
to a node-owned, read-only TUI session any paired tui-capable device can watch.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request


def test_relay_creates_attachable_shared_session(client: TestClient) -> None:
    relay = client.post(
        "/v1/runtime/tui/relay",
        json={
            "session_id": "agentsess_1",
            "agent_id": "agent_mock",
            "chunk": "$ echo hi\nhi\n",
        },
    )
    assert relay.status_code == 200, relay.text
    assert relay.json()["session_id"] == "agentsess_1"

    # Any paired tui-capable device can attach to the relay session, even though
    # it did not create it (node-owned, shared).
    paired = pair_device(client, requested_permissions=["read_state", "tui"])
    token = signed_request(
        client,
        "POST",
        "/v1/tui/sessions/agentsess_1/attach-token",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert token.status_code == 200, token.text

    # Re-feed is idempotent (same session).
    again = client.post(
        "/v1/runtime/tui/relay",
        json={"session_id": "agentsess_1", "agent_id": "agent_mock", "chunk": "more\n"},
    )
    assert again.status_code == 200


def test_relay_attach_requires_tui_capability(client: TestClient) -> None:
    client.post(
        "/v1/runtime/tui/relay",
        json={"session_id": "agentsess_2", "agent_id": "agent_mock", "chunk": "x\n"},
    )
    # A device without the tui capability cannot attach.
    paired = pair_device(client, requested_permissions=["read_state", "approve"])
    token = signed_request(
        client,
        "POST",
        "/v1/tui/sessions/agentsess_2/attach-token",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert token.status_code == 403
