from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import pair_device, signed_request
from hermes_gateway.app import create_app
from hermes_gateway.config import Settings


def test_low_risk_action_clears_from_local_terminal_when_enabled(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        approval = _create_approval(client, risk_family="read_only", risk_level="low")

        response = _local_decision(client, approval["approval_id"], decision="approve")

        assert response.status_code == 200
        assert response.json()["state"] == "approved"
        detail = client.app.state.store.get_approval(approval["approval_id"])
        assert detail["decision_metadata"]["channel"] == "local_terminal"
        assert detail["decision_metadata"]["risk_family"] == "read_only"


def test_low_risk_action_clears_from_mobile(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        paired = pair_device(client)
        approval = _create_approval(client, risk_family="routine", risk_level="low")

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/approve_once",
            private_key=paired["private_key"],
            device_id=paired["device"]["device_id"],
        )

        assert response.status_code == 200
        detail = client.app.state.store.get_approval(approval["approval_id"])
        assert detail["decision_metadata"]["channel"] == "mobile_signed"


def test_high_risk_action_rejects_local_terminal_in_both_mode(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        approval = _create_approval(
            client,
            risk_family="external_effect",
            risk_level="high",
        )

        response = _local_decision(client, approval["approval_id"], decision="approve")

        assert response.status_code == 403
        assert response.json()["detail"] == "channel_not_eligible_for_risk_family"
        assert client.app.state.store.get_approval(approval["approval_id"])["state"] == "pending"
        assert _audit_payloads(client, "clearance_channel_rejected")[0]["risk_family"] == (
            "external_effect"
        )


def test_high_risk_action_clears_from_mobile_in_both_mode(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        paired = pair_device(client)
        approval = _create_approval(
            client,
            risk_family="credential_or_secret",
            risk_level="critical",
        )

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/approve_once",
            private_key=paired["private_key"],
            device_id=paired["device"]["device_id"],
        )

        assert response.status_code == 200
        detail = client.app.state.store.get_approval(approval["approval_id"])
        assert detail["decision_metadata"]["channel"] == "mobile_signed"
        assert detail["decision_metadata"]["risk_family"] == "credential_or_secret"


def test_untrusted_host_rejects_all_local_terminal_clearances(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        _set_agent_trust(client, "untrusted_host")
        approval = _create_approval(client, risk_family="read_only", risk_level="low")

        response = _local_decision(client, approval["approval_id"], decision="approve")

        assert response.status_code == 403
        assert response.json()["detail"] == "local_terminal_disabled_for_trust_context"
        payload = _audit_payloads(client, "clearance_channel_rejected")[0]
        assert payload["deployment_trust_context"] == "untrusted_host"


def test_mobile_still_clears_for_untrusted_host(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        paired = pair_device(client)
        _set_agent_trust(client, "untrusted_host")
        approval = _create_approval(client, risk_family="destructive", risk_level="high")

        response = signed_request(
            client,
            "POST",
            f"/v1/approvals/{approval['approval_id']}/approve_once",
            private_key=paired["private_key"],
            device_id=paired["device"]["device_id"],
        )

        assert response.status_code == 200
        detail = client.app.state.store.get_approval(approval["approval_id"])
        assert detail["decision_metadata"]["deployment_trust_context"] == "untrusted_host"


def test_rejected_channel_is_audited_without_marking_approved(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        approval = _create_approval(client, risk_family="irreversible", risk_level="critical")

        response = _local_decision(client, approval["approval_id"], decision="approve")

        assert response.status_code == 403
        assert client.app.state.store.get_approval(approval["approval_id"])["state"] == "pending"
        payload = _audit_payloads(client, "clearance_channel_rejected")[0]
        assert payload["channel"] == "local_terminal"
        assert payload["eligibility_result"] == "rejected"


def test_every_issued_clearance_records_channel_and_risk_family(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        approval = _create_approval(client, risk_family="routine", risk_level="low")

        response = _local_decision(client, approval["approval_id"], decision="deny")

        assert response.status_code == 200
        payload = _audit_payloads(client, "approval_decision")[0]
        assert payload["channel"] == "local_terminal"
        assert payload["risk_family"] == "routine"


def test_both_mode_cannot_start_without_risk_tier_map(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        clearance_enabled_channels=("mobile_signed", "local_terminal"),
        clearance_local_terminal_enabled=True,
        clearance_risk_channel_map={},
    )

    with pytest.raises(ValueError, match="requires risk-tier map"):
        create_app(settings)


def test_aircraft_cannot_override_channel_rules(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        approval = _create_approval(
            client,
            risk_family="destructive",
            risk_level="high",
            channel_eligibility={"destructive": ["local_terminal"]},
        )

        response = _local_decision(client, approval["approval_id"], decision="approve")

        assert response.status_code == 403
        assert response.json()["detail"] == "channel_not_eligible_for_risk_family"


def test_deployment_trust_context_is_tower_configured_not_request_supplied(
    tmp_path: Path,
) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        _set_agent_trust(client, "untrusted_host")
        approval = _create_approval(
            client,
            risk_family="read_only",
            risk_level="low",
            deployment_trust_context="trusted_host",
        )

        response = _local_decision(client, approval["approval_id"], decision="approve")

        assert response.status_code == 403
        payload = _audit_payloads(client, "clearance_channel_rejected")[0]
        assert payload["deployment_trust_context"] == "untrusted_host"


def test_request_policy_override_attempt_is_ignored_and_audited(tmp_path: Path) -> None:
    with _policy_client(tmp_path, local_enabled=True) as client:
        response = client.post(
            "/v1/approvals",
            json=_approval_payload(
                risk_family="read_only",
                risk_level="low",
                deployment_trust_context="adversarial_host",
                channel_eligibility={"read_only": ["local_terminal"]},
            ),
        )

        assert response.status_code == 201
        payload = _audit_payloads(
            client,
            "clearance_request_policy_override_ignored",
        )[0]
        assert payload["attempted_deployment_trust_context"] == "adversarial_host"
        assert payload["attempted_channel_eligibility"] is True


def _policy_client(tmp_path: Path, *, local_enabled: bool) -> TestClient:
    return TestClient(
        create_app(
            _settings(
                tmp_path,
                clearance_enabled_channels=("mobile_signed", "local_terminal")
                if local_enabled
                else ("mobile_signed",),
                clearance_local_terminal_enabled=local_enabled,
            )
        ),
        client=("127.0.0.1", 50000),
    )


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "node_id": "node_policy",
        "node_display_name": "Policy Test Tower",
        "node_fingerprint": "policy-test-fingerprint",
        "gateway_base_url": "http://127.0.0.1:8787/v1",
        "database_path": str(tmp_path / "gateway.sqlite3"),
        "pairing_ttl_seconds": 60,
        "clearance_risk_channel_map": dict(Settings.default_clearance_risk_channel_map),
    }
    values.update(overrides)
    return Settings(**values)


def _create_approval(
    client: TestClient,
    *,
    risk_family: str,
    risk_level: str,
    deployment_trust_context: str | None = None,
    channel_eligibility: dict | None = None,
) -> dict:
    response = client.post(
        "/v1/approvals",
        json=_approval_payload(
            risk_family=risk_family,
            risk_level=risk_level,
            deployment_trust_context=deployment_trust_context,
            channel_eligibility=channel_eligibility,
        ),
    )
    assert response.status_code == 201
    return response.json()


def _approval_payload(
    *,
    risk_family: str,
    risk_level: str,
    deployment_trust_context: str | None = None,
    channel_eligibility: dict | None = None,
) -> dict:
    payload = {
        "action_id": f"act_{risk_family}",
        "agent_id": "agent_policy",
        "session_id": "work_policy",
        "requested_tool": "generic_operation",
        "risk_level": risk_level,
        "risk_family": risk_family,
        "summary": "Generic clearance request.",
        "full_payload_redacted": {"operation": "redacted"},
        "expires_at": "2099-01-01T00:00:00Z",
    }
    if deployment_trust_context:
        payload["deployment_trust_context"] = deployment_trust_context
    if channel_eligibility:
        payload["channel_eligibility"] = channel_eligibility
    return payload


def _local_decision(client: TestClient, approval_id: str, *, decision: str) -> object:
    return client.post(
        f"/v1/local-terminal/approvals/{approval_id}/decisions",
        json={
            "decision": decision,
            "scope": "once",
            "terminal_identity": "terminal_operator",
            "signature_verified": True,
        },
    )


def _set_agent_trust(client: TestClient, trust_context: str) -> None:
    client.app.state.store.upsert_agent(
        {
            "node_id": "node_policy",
            "agent_id": "agent_policy",
            "display_name": "Policy Test Agent",
            "status": "idle",
            "deployment_trust_context": trust_context,
        }
    )


def _audit_payloads(client: TestClient, event_type: str) -> list[dict]:
    return [
        event["payload_redacted"]
        for event in client.app.state.store.list_audit_events(event_type=event_type)
    ]
