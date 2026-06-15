from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request
from hermes_gateway.app import create_app
from hermes_gateway.config import Settings


def test_tua_request_session_message_return_and_close(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "intervene"])
    request = _create_tua_request(client)

    unsigned = client.get(f"/v1/tua/requests/{request['request_id']}")
    assert unsigned.status_code == 401

    get_response = _signed(
        client,
        paired,
        "GET",
        f"/v1/tua/requests/{request['request_id']}",
    )
    assert get_response.status_code == 200

    session_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/tua/requests/{request['request_id']}/sessions",
        json_body={"initial_message": "I can help from mobile."},
    )
    assert session_response.status_code == 201
    session = session_response.json()
    assert session["state"] == "active"
    assert len(session["messages"]) == 1

    message_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/tua/sessions/{session['assistance_session_id']}/messages",
        json_body={"body": "Try the safer path."},
    )
    assert message_response.status_code == 201

    return_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/tua/sessions/{session['assistance_session_id']}/return-control",
        json_body={"summary": "User advised a safer command."},
    )
    assert return_response.status_code == 200
    assert return_response.json()["state"] == "returned_to_agent"

    close_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/tua/sessions/{session['assistance_session_id']}/close",
    )
    assert close_response.status_code == 200
    assert close_response.json()["state"] == "closed"

    assert _audit_events(client, paired, "tua_request_created")
    assert _audit_events(client, paired, "tua_session_created")
    assert _events(client, paired, "tua.returned_to_agent")


def test_tua_hermes_local_caller_controls_enforced(tmp_path: Path) -> None:
    client = _client(tmp_path, caller_host="203.0.113.8")

    response = client.post("/v1/tua/requests", json=_tua_request_payload())

    assert response.status_code == 403
    assert "loopback" in response.json()["detail"]


def test_browser_assistance_session_return_and_audit(client: TestClient) -> None:
    paired = pair_device(
        client,
        requested_permissions=["read_state", "browser_assist"],
    )
    create_response = client.post(
        "/v1/browser-assistance/sessions",
        json={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "reason": "Browser submit needs human review.",
            "context_redacted": {"url": "https://example.invalid/form"},
        },
    )
    assert create_response.status_code == 201
    session = create_response.json()

    signed_fetch = _signed(
        client,
        paired,
        "GET",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}",
    )
    assert signed_fetch.status_code == 200

    event_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "User reviewed the form before submission."},
    )
    assert event_response.status_code == 200
    assert len(event_response.json()["user_action_notes"]) == 1

    return_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/return-control",
        json_body={"summary": "Reviewed; agent may continue."},
    )
    assert return_response.status_code == 200
    assert return_response.json()["state"] == "returned_to_agent"

    assert _audit_events(client, paired, "browser_assistance_returned_to_agent")
    assert _events(client, paired, "browser_assistance.returned_to_agent")


def test_advanced_approval_responses_and_policy_proposal(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "approve"])
    approval = _create_approval(client)

    modified = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/responses",
        json_body={
            "decision_type": "modified",
            "alternate_directive": "Delete only generated temp files.",
            "constraints": [
                {
                    "constraint_type": "path_allowlist",
                    "value_redacted": {"path": "./tmp"},
                }
            ],
        },
    )
    assert modified.status_code == 201
    assert modified.json()["decision_type"] == "modified"
    assert modified.json()["constraints"][0]["constraint_type"] == "path_allowlist"

    needs_info = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/responses",
        json_body={
            "decision_type": "needs_info",
            "user_message": "Show the exact affected files first.",
        },
    )
    assert needs_info.status_code == 201
    assert _events(client, paired, "approval.needs_info")

    no_confirmation = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/responses",
        json_body={"decision_type": "propose_policy"},
    )
    assert no_confirmation.status_code == 400

    policy = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/responses",
        json_body={
            "decision_type": "propose_policy",
            "confirmation_phrase": "PROPOSE POLICY",
            "constraints": [
                {
                    "constraint_type": "session_only",
                    "value_redacted": {"scope": "future-review"},
                }
            ],
        },
    )
    assert policy.status_code == 201
    assert policy.json()["policy_proposal_id"]

    proposals = _signed(
        client,
        paired,
        "GET",
        f"/v1/approvals/{approval['approval_id']}/policy-proposals",
    )
    assert proposals.status_code == 200
    assert proposals.json()["policy_proposals"][0]["status"] == "proposed"
    assert "no permanent allow policy" in proposals.json()["policy_proposals"][0]["warning"]
    assert _audit_events(client, paired, "approval_response_created")


def test_voice_session_message_and_close(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "voice"])

    unsigned = client.post("/v1/voice/sessions", json={"agent_id": "agent_mock"})
    assert unsigned.status_code == 401

    create_response = _signed(
        client,
        paired,
        "POST",
        "/v1/voice/sessions",
        json_body={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "mode": "text_fallback",
        },
    )
    assert create_response.status_code == 201
    session = create_response.json()
    assert session["state"] == "active"

    message_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/voice/sessions/{session['voice_session_id']}/messages",
        json_body={"body": "Pause that mission.", "input_mode": "text_fallback"},
    )
    assert message_response.status_code == 201
    assert message_response.json()["input_mode"] == "text_fallback"

    close_response = _signed(
        client,
        paired,
        "POST",
        f"/v1/voice/sessions/{session['voice_session_id']}/close",
    )
    assert close_response.status_code == 200
    assert close_response.json()["state"] == "closed"

    assert _audit_events(client, paired, "voice_session_created")
    assert _events(client, paired, "voice.session.closed")


def _create_tua_request(client: TestClient) -> dict:
    response = client.post("/v1/tua/requests", json=_tua_request_payload())
    assert response.status_code == 201
    return response.json()


def _tua_request_payload() -> dict:
    return {
        "agent_id": "agent_mock",
        "session_id": "sess_mock",
        "reason": "Agent needs operator assistance.",
        "context_redacted": {"tool": "shell"},
    }


def _create_approval(client: TestClient) -> dict:
    response = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "shell",
            "risk_level": "high",
            "risk_family": "destructive",
            "summary": "Delete generated build output.",
            "payload_redacted": {"command": "rm -rf ./dist"},
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "expires_in_seconds": 300,
            "suggested_scopes": ["once", "session", "agent"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _signed(
    client: TestClient,
    paired: dict,
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
) -> object:
    return signed_request(
        client,
        method,
        path,
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
        json_body=json_body,
    )


def _audit_events(client: TestClient, paired: dict, event_type: str) -> list[dict]:
    response = _signed(client, paired, "GET", f"/v1/audit/events?event_type={event_type}")
    assert response.status_code == 200
    return response.json()["audit_events"]


def _events(client: TestClient, paired: dict, event_type: str) -> list[dict]:
    response = _signed(client, paired, "GET", "/v1/events")
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["type"] == event_type]


def _client(
    tmp_path: Path,
    *,
    caller_host: str,
    allowed_hermes_callers: tuple[str, ...] = (),
) -> TestClient:
    settings = Settings(
        node_id="node_operator_caps",
        node_display_name="Operator Capability Test Hermes",
        node_fingerprint="operator-capability-fingerprint",
        gateway_base_url="http://127.0.0.1:8787/v1",
        database_path=str(tmp_path / f"{caller_host.replace('.', '_')}.sqlite3"),
        allowed_hermes_callers=allowed_hermes_callers,
    )
    return TestClient(create_app(settings), client=(caller_host, 50000))
