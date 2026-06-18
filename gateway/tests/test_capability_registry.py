from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from conftest import b64url, pair_device, signed_request
from hermes_gateway.app import create_app
from hermes_gateway.clearance_contract import proof_material_from_approval
from hermes_gateway.config import Settings


def test_gate_unknown_capability_no_longer_accepts_aircraft_low_risk_label(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")

        approval = _create_approval(
            client,
            capability="browser.live_form_submit",
            risk_family="routine",
            risk_level="low",
        )

        assert approval["risk_family"] == "external_effect"
        response = _local_decision(client, approval["approval_id"], decision="approve")
        assert response.status_code == 403
        assert response.json()["detail"] == "channel_not_eligible_for_risk_family"


def test_gate_capability_registry_is_authoritative_over_request_risk_family(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")
        _approve_capability_pin(
            client,
            capability="browser.live_form_submit",
            risk_family="external_effect",
        )

        response = client.post(
            "/v1/approvals",
            json=_approval_payload(
                capability="browser.live_form_submit",
                risk_family="routine",
                risk_level="low",
            ),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "capability_risk_mismatch"


def test_matching_approved_pin_proceeds_at_resolved_risk_and_mobile_clears(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")
        _approve_capability_pin(
            client,
            capability="browser.live_form_submit",
            risk_family="external_effect",
        )

        approval = _create_approval(
            client,
            capability="browser.live_form_submit",
            risk_family="external_effect",
            risk_level="high",
        )

        assert approval["risk_family"] == "external_effect"
        assert approval["capability"] == "browser.live_form_submit"
        assert proof_material_from_approval(approval).risk_family == "external_effect"
        mobile = pair_device(client)
        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/approve_once",
            private_key=mobile["private_key"],
            device_id=mobile["device"]["device_id"],
        )
        assert response.status_code == 200


def test_mismatch_in_either_direction_rejects_and_escalates(tmp_path: Path) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")
        _approve_capability_pin(
            client,
            capability="filesystem.delete",
            risk_family="destructive",
        )

        lower = client.post(
            "/v1/approvals",
            json=_approval_payload(
                capability="filesystem.delete",
                risk_family="routine",
                risk_level="low",
            ),
        )
        higher = client.post(
            "/v1/approvals",
            json=_approval_payload(
                capability="filesystem.delete",
                risk_family="irreversible",
                risk_level="critical",
            ),
        )

        assert lower.status_code == 409
        assert higher.status_code == 409
        audit_payloads = _audit_payloads(client, "capability_risk_mismatch")
        assert {payload["severity"] for payload in audit_payloads} == {"security", "drift"}
        assert all("filesystem.delete" in payload["capability"] for payload in audit_payloads)


def test_unknown_capability_hard_rejects_when_agent_requires_classification(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(
            client,
            trust_context="trusted_host",
            require_classified_capabilities=True,
        )

        response = client.post(
            "/v1/approvals",
            json=_approval_payload(
                capability="browser.live_form_submit",
                risk_family="routine",
                risk_level="low",
            ),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "capability_unclassified"
        assert _audit_payloads(client, "capability_unclassified")[0]["severity"] == "classify"


def test_pending_and_downgrade_proposals_do_not_change_effective_pin(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")
        _approve_capability_pin(
            client,
            capability="vm.power_cycle",
            risk_family="destructive",
        )
        pending = client.post(
            "/v1/capability-registry/proposals",
            json={
                "node_id": "node_capability",
                "agent_id": "agent_capability",
                "entries": [{"capability": "vm.power_cycle", "risk_family": "routine"}],
            },
        )
        assert pending.status_code == 201

        response = client.post(
            "/v1/approvals",
            json=_approval_payload(
                capability="vm.power_cycle",
                risk_family="routine",
                risk_level="low",
            ),
        )

        assert response.status_code == 409
        entry = pending.json()["entries"][0]
        operator = pair_device(client, requested_permissions=["read_state", "manage_capabilities"])
        approval = signed_request(
            client,
            "POST",
            f"/v1/capability-registry/{entry['entry_id']}/decision",
            private_key=operator["private_key"],
            device_id=operator["device"]["device_id"],
            json_body={"decision": "approve"},
        )
        assert approval.status_code == 200
        lowered = _create_approval(
            client,
            capability="vm.power_cycle",
            risk_family="routine",
            risk_level="low",
        )
        assert lowered["risk_family"] == "routine"


def test_operator_approval_requires_manage_capabilities_permission(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client)
        proposal = client.post(
            "/v1/capability-registry/proposals",
            json={
                "node_id": "node_capability",
                "agent_id": "agent_capability",
                "entries": [{"capability": "vm.power_cycle", "risk_family": "destructive"}],
            },
        )
        assert proposal.status_code == 201
        entry = proposal.json()["entries"][0]
        no_permission = pair_device(client, requested_permissions=["read_state", "approve"])

        response = signed_request(
            client,
            "POST",
            f"/v1/capability-registry/{entry['entry_id']}/decision",
            private_key=no_permission["private_key"],
            device_id=no_permission["device"]["device_id"],
            json_body={"decision": "approve"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "device lacks manage_capabilities permission"


def test_v1_extension_capability_is_supported_with_deprecation_audit(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")
        response = client.post(
            "/v1/approvals",
            json={
                "action_id": "act_extension_capability",
                "agent_id": "agent_capability",
                "session_id": "work_capability",
                "requested_tool": "generic_operation",
                "risk_level": "high",
                "risk_family": "external_effect",
                "summary": "Capability-registry clearance request.",
                "full_payload_redacted": {"operation": "redacted"},
                "extensions": {
                    "agentickvm": {
                        "capability": "vm.power_cycle",
                        "target": "vm-alpha",
                    }
                },
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )

        assert response.status_code == 201
        approval = response.json()
        assert approval["capability"] == "vm.power_cycle"
        audit_text = str(_audit_payloads(client, "approval_requested")[0])
        assert "capability_extension" in audit_text


def test_capability_alerts_do_not_include_raw_aircraft_text(tmp_path: Path) -> None:
    with _policy_client(tmp_path) as client:
        _set_agent(client, trust_context="trusted_host")
        raw = "unsafe capability token=abc123SECRETvalue"

        response = client.post(
            "/v1/approvals",
            json=_approval_payload(
                capability=raw,
                risk_family="routine",
                risk_level="low",
            ),
        )

        assert response.status_code == 201
        audit = _audit_payloads(client, "capability_unclassified")[0]
        assert "abc123" not in str(audit)


def _policy_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                node_id="node_capability",
                node_display_name="Capability Test Tower",
                node_fingerprint="capability-test-fingerprint",
                gateway_base_url="http://127.0.0.1:8787/v1",
                database_path=str(tmp_path / "gateway.sqlite3"),
                pairing_ttl_seconds=60,
                clearance_enabled_channels=("mobile_signed", "local_terminal"),
                clearance_local_terminal_enabled=True,
                clearance_risk_channel_map=dict(Settings.default_clearance_risk_channel_map),
            )
        ),
        client=("127.0.0.1", 50000),
    )


def _create_approval(
    client: TestClient,
    *,
    capability: str,
    risk_family: str,
    risk_level: str,
) -> dict:
    response = client.post(
        "/v1/approvals",
        json=_approval_payload(
            capability=capability,
            risk_family=risk_family,
            risk_level=risk_level,
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _approval_payload(*, capability: str, risk_family: str, risk_level: str) -> dict:
    return {
        "action_id": f"act_{capability}",
        "agent_id": "agent_capability",
        "session_id": "work_capability",
        "requested_tool": "generic_operation",
        "capability": capability,
        "risk_level": risk_level,
        "risk_family": risk_family,
        "summary": "Capability-registry clearance request.",
        "full_payload_redacted": {"operation": "redacted", "capability": capability},
        "expires_at": "2099-01-01T00:00:00Z",
    }


def _set_agent(
    client: TestClient,
    *,
    trust_context: str = "untrusted_host",
    require_classified_capabilities: bool = False,
) -> None:
    client.app.state.store.upsert_agent(
        {
            "node_id": "node_capability",
            "agent_id": "agent_capability",
            "display_name": "Capability Test Agent",
            "status": "idle",
            "deployment_trust_context": trust_context,
            "require_classified_capabilities": require_classified_capabilities,
        }
    )


def _local_decision(client: TestClient, approval_id: str, *, decision: str) -> object:
    terminal = _terminal_principal(client)
    return signed_request(
        client,
        "POST",
        f"/v1/local-terminal/approvals/{approval_id}/decisions",
        private_key=terminal["private_key"],
        device_id=terminal["device"]["device_id"],
        json_body={"decision": decision, "scope": "once"},
    )


def _terminal_principal(client: TestClient) -> dict:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    device = client.app.state.store.create_device(
        node_id="node_capability",
        device_name="Terminal",
        platform="local_terminal",
        app_instance_id=f"terminal-{id(private_key)}",
        app_version="0.1.0",
        device_public_key=b64url(public_key),
        permissions=["read_state", "approve"],
        clearance_channel="local_terminal",
    )
    return {"device": device, "private_key": private_key}


def _approve_capability_pin(
    client: TestClient,
    *,
    capability: str,
    risk_family: str,
) -> dict:
    proposal = client.post(
        "/v1/capability-registry/proposals",
        json={
            "node_id": "node_capability",
            "agent_id": "agent_capability",
            "entries": [{"capability": capability, "risk_family": risk_family}],
        },
    )
    assert proposal.status_code == 201, proposal.text
    entry = proposal.json()["entries"][0]
    operator = pair_device(client, requested_permissions=["read_state", "manage_capabilities"])
    decision = signed_request(
        client,
        "POST",
        f"/v1/capability-registry/{entry['entry_id']}/decision",
        private_key=operator["private_key"],
        device_id=operator["device"]["device_id"],
        json_body={"decision": "approve"},
    )
    assert decision.status_code == 200, decision.text
    return decision.json()


def _audit_payloads(client: TestClient, event_type: str) -> list[dict]:
    return [
        event["payload_redacted"]
        for event in client.app.state.store.list_audit_events(event_type=event_type)
    ]
