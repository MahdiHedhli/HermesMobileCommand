from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from conftest import b64url, pair_device, signed_request
from hermes_gateway.app import create_app
from hermes_gateway.clearance_policy import risk_family_from_request
from hermes_gateway.config import Settings


def test_local_principal_cannot_clear_high_risk_via_mobile_route(tmp_path: Path) -> None:
    with _client(tmp_path, local_enabled=True) as client:
        terminal = _register_terminal_principal(client)
        approval = _create_approval(client, risk_family="destructive", risk_level="high")

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/approve_once",
            private_key=terminal["private_key"],
            device_id=terminal["device"]["device_id"],
        )

        assert response.status_code == 403


def test_local_endpoint_rejects_client_supplied_signature_boolean(
    tmp_path: Path,
) -> None:
    with _client(tmp_path, local_enabled=True) as client:
        approval = _create_approval(client, risk_family="read_only", risk_level="low")

        response = client.post(
            f"/v1/local-terminal/approvals/{approval['approval_id']}/decisions",
            json={
                "decision": "approve",
                "scope": "once",
                "terminal_identity": "attacker_supplied",
                "signature_verified": True,
            },
        )

        assert response.status_code == 401


def test_local_terminal_can_deny_high_risk(tmp_path: Path) -> None:
    with _client(tmp_path, local_enabled=True) as client:
        terminal = _register_terminal_principal(client)
        approval = _create_approval(client, risk_family="destructive", risk_level="high")

        response = signed_request(
            client,
            "POST",
            f"/v1/local-terminal/approvals/{approval['approval_id']}/decisions",
            private_key=terminal["private_key"],
            device_id=terminal["device"]["device_id"],
            json_body={
                "decision": "deny",
                "scope": "once",
            },
        )

        assert response.status_code == 200


def test_fresh_agent_defaults_untrusted(tmp_path: Path) -> None:
    with _client(tmp_path, local_enabled=True) as client:
        agent = client.app.state.store.upsert_agent(
            {
                "node_id": "node_gate",
                "agent_id": "agent_gate",
                "display_name": "Gate Agent",
                "status": "idle",
            }
        )

        assert agent["deployment_trust_context"] == "untrusted_host"


def test_unlabeled_risk_defaults_mobile_mandatory() -> None:
    assert (
        risk_family_from_request(
            risk_family=None,
            risk_category=None,
            risk_level="low",
        )
        == "external_effect"
    )


def _client(tmp_path: Path, *, local_enabled: bool) -> TestClient:
    settings = Settings(
        node_id="node_gate",
        node_display_name="Gate Tower",
        node_fingerprint="gate-fingerprint",
        gateway_base_url="http://127.0.0.1:8787/v1",
        database_path=str(tmp_path / "gateway.sqlite3"),
        clearance_enabled_channels=("mobile_signed", "local_terminal")
        if local_enabled
        else ("mobile_signed",),
        clearance_local_terminal_enabled=local_enabled,
        clearance_risk_channel_map=dict(Settings.default_clearance_risk_channel_map),
    )
    return TestClient(create_app(settings), client=("127.0.0.1", 50000))


def _register_terminal_principal(client: TestClient) -> dict:
    paired = pair_device(client)
    paired["device"] = client.app.state.store.create_device(
        node_id="node_gate",
        device_name="Terminal",
        platform="local_terminal",
        app_instance_id="terminal-gate",
        app_version="0.1.0",
        device_public_key=b64url(
            paired["private_key"]
            .public_key()
            .public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ),
        permissions=["read_state", "approve"],
        clearance_channel="local_terminal",
    )
    return paired


def _create_approval(
    client: TestClient,
    *,
    risk_family: str,
    risk_level: str,
) -> dict:
    response = client.post(
        "/v1/approvals",
        json={
            "action_id": f"act_{risk_family}",
            "agent_id": "agent_gate",
            "session_id": "work_gate",
            "requested_tool": "generic_operation",
            "risk_level": risk_level,
            "risk_family": risk_family,
            "summary": "Gate clearance request.",
            "full_payload_redacted": {"operation": "redacted"},
            "expires_at": "2099-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201
    return response.json()
