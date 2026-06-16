from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

import hermes_gateway.app as app_module
from conftest import b64url, pair_device, signed_request
from hermes_gateway.app import create_app
from hermes_gateway.config import Settings


def test_mobile_decision_route_uses_clearance_enforcement_chokepoint(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    with _policy_client(tmp_path) as client:
        calls = _spy_enforcement(monkeypatch)
        paired = pair_device(client)
        approval = _create_approval(client)

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/decisions",
            private_key=paired["private_key"],
            device_id=paired["device"]["device_id"],
            json_body={
                "decision_id": "decision_route",
                "decision": "approve",
                "scope": "session",
                "signed_payload": {
                    "approval_id": approval["approval_id"],
                    "params_fingerprint": approval["params_fingerprint"],
                },
                "signature": "covered-by-device-request-signature",
            },
        )

        assert response.status_code == 200
        assert response.json()["state"] == "approved"
        assert calls == [
            {
                "approval_id": approval["approval_id"],
                "channel": "mobile_signed",
                "actor_id": paired["device"]["device_id"],
            }
        ]


def test_mobile_approve_once_route_uses_clearance_enforcement_chokepoint(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    with _policy_client(tmp_path) as client:
        calls = _spy_enforcement(monkeypatch)
        paired = pair_device(client)
        approval = _create_approval(client)

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/approve_once",
            private_key=paired["private_key"],
            device_id=paired["device"]["device_id"],
        )

        assert response.status_code == 200
        assert response.json()["state"] == "approved"
        assert calls == [
            {
                "approval_id": approval["approval_id"],
                "channel": "mobile_signed",
                "actor_id": paired["device"]["device_id"],
            }
        ]


def test_advanced_approval_response_route_uses_clearance_enforcement_chokepoint(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    with _policy_client(tmp_path) as client:
        calls = _spy_enforcement(monkeypatch)
        paired = pair_device(client)
        approval = _create_approval(client)

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/responses",
            private_key=paired["private_key"],
            device_id=paired["device"]["device_id"],
            json_body={
                "decision_type": "approve_agent",
                "params_fingerprint": approval["params_fingerprint"],
            },
        )

        assert response.status_code == 201
        assert client.app.state.store.get_approval(approval["approval_id"])["state"] == "approved"
        assert calls == [
            {
                "approval_id": approval["approval_id"],
                "channel": "mobile_signed",
                "actor_id": paired["device"]["device_id"],
            }
        ]


def test_local_terminal_decision_route_uses_clearance_enforcement_chokepoint(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    with _policy_client(tmp_path) as client:
        calls = _spy_enforcement(monkeypatch)
        _set_agent_trust(client, "trusted_host")
        terminal = _terminal_principal(client)
        approval = _create_approval(client, risk_family="routine", risk_level="low")

        response = signed_request(
            client,
            "POST",
            f"/v1/local-terminal/approvals/{approval['approval_id']}/decisions",
            private_key=terminal["private_key"],
            device_id=terminal["device"]["device_id"],
            json_body={"decision": "approve", "scope": "once"},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "approved"
        assert calls == [
            {
                "approval_id": approval["approval_id"],
                "channel": "local_terminal",
                "actor_id": terminal["device"]["device_id"],
            }
        ]


def _spy_enforcement(monkeypatch: Any) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    original: Callable[..., Any] = app_module.enforce_clearance_channel

    def spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(
            {
                "approval_id": kwargs["approval"]["approval_id"],
                "channel": kwargs["channel"],
                "actor_id": kwargs["actor_id"],
            }
        )
        return original(*args, **kwargs)

    monkeypatch.setattr(app_module, "enforce_clearance_channel", spy)
    return calls


def _policy_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        node_id="node_chokepoint",
        node_display_name="Chokepoint Test Tower",
        node_fingerprint="chokepoint-test-fingerprint",
        gateway_base_url="http://127.0.0.1:8787/v1",
        database_path=str(tmp_path / "gateway.sqlite3"),
        pairing_ttl_seconds=60,
        clearance_enabled_channels=("mobile_signed", "local_terminal"),
        clearance_local_terminal_enabled=True,
        clearance_risk_channel_map=dict(Settings.default_clearance_risk_channel_map),
    )
    return TestClient(create_app(settings), client=("127.0.0.1", 50000))


def _create_approval(
    client: TestClient,
    *,
    risk_family: str = "external_effect",
    risk_level: str = "high",
) -> dict[str, Any]:
    response = client.post(
        "/v1/approvals",
        json={
            "action_id": f"act_chokepoint_{risk_family}",
            "agent_id": "agent_chokepoint",
            "session_id": "work_chokepoint",
            "requested_tool": "generic_operation",
            "risk_level": risk_level,
            "risk_family": risk_family,
            "summary": "Generic clearance request.",
            "full_payload_redacted": {"operation": "redacted"},
            "expires_at": "2099-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201
    return response.json()


def _terminal_principal(client: TestClient) -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    device = client.app.state.store.create_device(
        node_id="node_chokepoint",
        device_name="Terminal",
        platform="local_terminal",
        app_instance_id=f"terminal-{id(private_key)}",
        app_version="0.1.0",
        device_public_key=b64url(public_key),
        permissions=["read_state", "approve"],
        clearance_channel="local_terminal",
    )
    return {"device": device, "private_key": private_key}


def _set_agent_trust(client: TestClient, trust_context: str) -> None:
    client.app.state.store.upsert_agent(
        {
            "node_id": "node_chokepoint",
            "agent_id": "agent_chokepoint",
            "display_name": "Chokepoint Test Agent",
            "status": "idle",
            "deployment_trust_context": trust_context,
        }
    )
