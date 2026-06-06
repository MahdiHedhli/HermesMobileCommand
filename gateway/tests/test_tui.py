from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from conftest import pair_device, signed_request
from hermes_gateway.app import create_app
from hermes_gateway.config import Settings


@pytest.fixture()
def tui_client(tmp_path: Path) -> TestClient:
    command = _cat_command()
    settings = Settings(
        node_id="node_tui",
        node_display_name="TUI Hermes",
        node_fingerprint="tui-fingerprint",
        gateway_base_url="http://127.0.0.1:8787/v1",
        database_path=str(tmp_path / "gateway.sqlite3"),
        pairing_ttl_seconds=60,
        tui_enable_local_pty=True,
        tui_allowed_commands=(command,),
        tui_default_command=command,
        tui_allowed_working_directory=str(tmp_path),
        tui_max_sessions=3,
    )
    with TestClient(create_app(settings), client=("127.0.0.1", 50000)) as test_client:
        yield test_client


def test_tui_disabled_by_default(client: TestClient) -> None:
    paired = pair_device(client)

    response = signed_request(
        client,
        "POST",
        "/v1/tui/sessions",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
        json_body={"agent_id": "agent_mock"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "local TUI PTY is disabled"


def test_tui_signed_request_required(client: TestClient) -> None:
    response = client.post("/v1/tui/sessions", json={"agent_id": "agent_mock"})

    assert response.status_code == 401
    assert response.json()["detail"] == "missing device signature"


def test_tui_revoked_device_rejected(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)
    device_id = paired["device"]["device_id"]
    revoke = signed_request(
        tui_client,
        "DELETE",
        f"/v1/devices/{device_id}",
        private_key=paired["private_key"],
        device_id=device_id,
    )
    assert revoke.status_code == 204

    response = _signed_create_tui(tui_client, paired)

    assert response.status_code == 403
    assert response.json()["detail"] == "device is not active"


def test_tui_session_creation_when_enabled(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)

    response = _signed_create_tui(tui_client, paired)

    assert response.status_code == 201
    session = response.json()
    assert session["state"] == "active"
    assert session["user_device_id"] == paired["device"]["device_id"]
    _signed_close_tui(tui_client, paired, session["session_id"])


def test_tui_command_not_allowlisted_rejected(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)

    response = _signed_create_tui(tui_client, paired, command="/bin/sh")

    assert response.status_code == 403
    assert response.json()["detail"] == "TUI command is not allowlisted"


def test_tui_working_directory_outside_allowed_root_rejected(
    tui_client: TestClient,
) -> None:
    paired = pair_device(tui_client)

    response = _signed_create_tui(tui_client, paired, working_directory="/")

    assert response.status_code == 403
    assert response.json()["detail"] == "TUI working directory is outside the allowed root"


def test_tui_detach_creates_audit_event(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)
    session = _signed_create_tui(tui_client, paired).json()

    response = signed_request(
        tui_client,
        "POST",
        f"/v1/tui/sessions/{session['session_id']}/detach",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )

    assert response.status_code == 200
    assert response.json()["session"]["state"] == "detached"
    audit = _signed_audit_events(tui_client, paired, "tui_session_detached")
    assert audit["audit_events"]
    _signed_close_tui(tui_client, paired, session["session_id"])


def test_tui_close_creates_audit_event(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)
    session = _signed_create_tui(tui_client, paired).json()

    response = _signed_close_tui(tui_client, paired, session["session_id"])

    assert response.status_code == 200
    assert response.json()["session"]["state"] == "closed"
    audit = _signed_audit_events(tui_client, paired, "tui_session_closed")
    assert audit["audit_events"]


def test_tui_websocket_rejects_invalid_session(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)
    token = paired["tokens"]["access_token"]

    with pytest.raises(WebSocketDisconnect):
        with tui_client.websocket_connect(
            f"/v1/tui/sessions/tui_missing/stream?access_token={token}"
        ):
            pass


def test_tui_websocket_basic_pty_output_smoke(tui_client: TestClient) -> None:
    paired = pair_device(tui_client)
    session = _signed_create_tui(tui_client, paired).json()
    token = paired["tokens"]["access_token"]

    with tui_client.websocket_connect(
        f"/v1/tui/sessions/{session['session_id']}/stream?access_token={token}"
    ) as websocket:
        assert websocket.receive_json()["type"] == "state"
        assert websocket.receive_json()["type"] == "audit_notice"
        websocket.send_json({"type": "input", "data": "hmcp_tui_smoke\n"})

        output = ""
        for _ in range(20):
            message = websocket.receive_json()
            if message["type"] == "output":
                output += message["data"]
            if "hmcp_tui_smoke" in output:
                break

        websocket.send_json({"type": "close"})

    assert "hmcp_tui_smoke" in output


def _signed_create_tui(
    client: TestClient,
    paired: dict,
    *,
    command: str | None = None,
    working_directory: str | None = None,
) -> object:
    return signed_request(
        client,
        "POST",
        "/v1/tui/sessions",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
        json_body={
            "agent_id": "agent_mock",
            "command": command,
            "working_directory": working_directory,
        },
    )


def _signed_close_tui(client: TestClient, paired: dict, session_id: str) -> object:
    return signed_request(
        client,
        "POST",
        f"/v1/tui/sessions/{session_id}/close",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )


def _signed_audit_events(client: TestClient, paired: dict, event_type: str) -> dict:
    response = signed_request(
        client,
        "GET",
        f"/v1/audit/events?event_type={event_type}",
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
    )
    assert response.status_code == 200
    return response.json()


def _cat_command() -> str:
    command = shutil.which("cat")
    if command is None:
        pytest.skip("cat command is unavailable for PTY smoke tests")
    return command
