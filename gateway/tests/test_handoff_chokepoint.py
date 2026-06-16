from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

import hermes_gateway.app as app_module
import hermes_gateway.runtime_adapter as runtime_adapter_module
from conftest import pair_device, signed_request


def test_tua_session_route_uses_handoff_engage_chokepoint(
    client: TestClient,
    monkeypatch: Any,
) -> None:
    calls = _spy_app_engage(monkeypatch)
    paired = pair_device(client, requested_permissions=["read_state", "intervene"])
    request = _create_tua_request(client, risk_family="read_only")

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/tua/requests/{request['request_id']}/sessions",
        json_body={"initial_message": "I can help."},
    )

    assert response.status_code == 201
    assert calls == [{"handoff_kind": "operator_guidance", "risk_family": "read_only"}]


def test_browser_event_route_uses_handoff_engage_chokepoint(
    client: TestClient,
    monkeypatch: Any,
) -> None:
    calls = _spy_app_engage(monkeypatch)
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    session = _create_browser_session(client, risk_family="read_only")

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Reviewed."},
    )

    assert response.status_code == 200
    assert calls == [{"handoff_kind": "browser_review", "risk_family": "read_only"}]


def test_voice_session_route_uses_handoff_engage_chokepoint(
    client: TestClient,
    monkeypatch: Any,
) -> None:
    calls = _spy_app_engage(monkeypatch)
    paired = pair_device(client, requested_permissions=["read_state", "voice"])

    response = _signed(
        client,
        paired,
        "POST",
        "/v1/voice/sessions",
        json_body={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "mode": "text_fallback",
            "risk_family": "read_only",
        },
    )

    assert response.status_code == 201
    assert calls == [{"handoff_kind": "voice_prompt", "risk_family": "read_only"}]


def test_runtime_voice_route_uses_handoff_engage_chokepoint(
    client: TestClient,
    monkeypatch: Any,
) -> None:
    calls = _spy_runtime_engage(monkeypatch)
    client.app.state.store.upsert_agent(
        {
            "node_id": "node_test",
            "agent_id": "agent_mock",
            "display_name": "Mock Agent",
            "status": "idle",
            "capabilities": [{"name": "voice", "status": "available"}],
        }
    )

    response = client.post(
        "/v1/runtime/voice/sessions",
        json={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "mode": "text_fallback",
            "risk_family": "read_only",
        },
    )

    assert response.status_code == 201
    assert calls == [{"handoff_kind": "voice_prompt", "risk_family": "read_only"}]


def _spy_app_engage(monkeypatch: Any) -> list[dict[str, str]]:
    return _spy_engage(monkeypatch, app_module)


def _spy_runtime_engage(monkeypatch: Any) -> list[dict[str, str]]:
    return _spy_engage(monkeypatch, runtime_adapter_module)


def _spy_engage(monkeypatch: Any, module: Any) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    original: Callable[..., dict[str, Any]] = module._engage_handoff

    def spy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(
            {
                "handoff_kind": kwargs["handoff_kind"],
                "risk_family": kwargs["risk_family"],
            }
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_engage_handoff", spy)
    return calls


def _create_tua_request(client: TestClient, *, risk_family: str) -> dict:
    response = client.post(
        "/v1/tua/requests",
        json={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "reason": "Agent needs operator guidance.",
            "risk_family": risk_family,
            "context_redacted": {},
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_browser_session(client: TestClient, *, risk_family: str) -> dict:
    response = client.post(
        "/v1/browser-assistance/sessions",
        json={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "reason": "Browser review requested.",
            "risk_family": risk_family,
            "context_redacted": {},
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
