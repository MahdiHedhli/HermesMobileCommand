from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from hermes_gateway.app import create_app
from hermes_gateway.config import Settings


def test_loopback_hermes_local_calls_allowed(tmp_path: Path) -> None:
    client = _client(tmp_path, caller_host="127.0.0.1")

    response = _mobile_notify(client)

    assert response.status_code == 202


def test_non_loopback_hermes_local_calls_rejected_by_default(tmp_path: Path) -> None:
    client = _client(tmp_path, caller_host="203.0.113.7")

    response = _mobile_notify(client)

    assert response.status_code == 403
    assert "loopback" in response.json()["detail"]


def test_explicit_hermes_caller_allowlist_allows_non_loopback(tmp_path: Path) -> None:
    client = _client(
        tmp_path,
        caller_host="203.0.113.7",
        allowed_hermes_callers=("203.0.113.7",),
    )

    response = _mobile_notify(client)

    assert response.status_code == 202


def _client(
    tmp_path: Path,
    *,
    caller_host: str,
    allowed_hermes_callers: tuple[str, ...] = (),
) -> TestClient:
    settings = Settings(
        node_id="node_binding",
        node_display_name="Binding Test Hermes",
        node_fingerprint="binding-fingerprint",
        gateway_base_url="http://127.0.0.1:8787/v1",
        database_path=str(tmp_path / f"{caller_host.replace('.', '_')}.sqlite3"),
        allowed_hermes_callers=allowed_hermes_callers,
    )
    return TestClient(create_app(settings), client=(caller_host, 50000))


def _mobile_notify(client: TestClient):
    return client.post(
        "/v1/notifications/mobile_notify",
        json={
            "title": "Health",
            "body": "Gateway health changed.",
            "urgency": "normal",
            "category": "system_health",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
        },
    )
