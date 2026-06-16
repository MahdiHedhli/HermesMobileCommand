from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import pair_device, signed_request
from hermes_gateway.runtime_adapter import RuntimeHandoffRequest
from hermes_gateway.schemas import (
    CreateAssistanceRequest,
    CreateBrowserAssistanceSessionRequest,
)
from hermes_gateway.security import content_hash


def test_high_risk_browser_handoff_requires_bound_clearance(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    session = _create_browser_session(client, approval_id=None)

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over the high-risk browser action."},
    )

    assert response.status_code == 403
    assert client.app.state.store.get_browser_assistance_session(
        session["browser_session_id"]
    )["state"] == "requested"


def test_high_risk_browser_handoff_rejects_denied_clearance(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "approve", "browser_assist"])
    approval = _create_approval(client)
    denied = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/deny",
    )
    assert denied.status_code == 200
    session = _create_browser_session(client, approval_id=approval["approval_id"])

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over with a denied clearance."},
    )

    assert response.status_code == 403
    assert client.app.state.store.get_browser_assistance_session(
        session["browser_session_id"]
    )["state"] == "requested"


def test_high_risk_browser_handoff_rejects_nonexistent_clearance(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    session = _create_browser_session(client, approval_id="appr_missing")

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over with a missing clearance."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "clearance_not_found"


def test_high_risk_browser_handoff_rejects_mismatched_work_clearance(
    client: TestClient,
) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "approve", "browser_assist"])
    approval = _create_approval(client, session_id="sess_other")
    approved = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
    )
    assert approved.status_code == 200
    session = _create_browser_session(client, approval_id=approval["approval_id"])

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over with another work unit's clearance."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "same_work"


def test_high_risk_browser_handoff_rejects_expired_clearance(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    approval = _seed_approved_clearance(
        client,
        expires_at="2000-01-01T00:00:00Z",
        metadata={
            "channel": "mobile_signed",
            "risk_family": "external_effect",
            "eligible_channels": ["mobile_signed"],
            "eligibility_result": "allowed",
        },
    )
    session = _create_browser_session(client, approval_id=approval["approval_id"])

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over with an expired clearance."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "not_expired"


def test_high_risk_browser_handoff_rejects_local_terminal_backed_clearance(
    client: TestClient,
) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    approval = _seed_approved_clearance(
        client,
        metadata={
            "channel": "local_terminal",
            "risk_family": "read_only",
            "eligible_channels": ["mobile_signed", "local_terminal"],
            "eligibility_result": "allowed",
        },
    )
    session = _create_browser_session(client, approval_id=approval["approval_id"])

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over with a local-terminal clearance."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "same_risk_family"


def test_high_risk_browser_handoff_accepts_mobile_tiered_bound_clearance(
    client: TestClient,
) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "approve", "browser_assist"])
    approval = _create_approval(client)
    approved = _signed(
        client,
        paired,
        "POST",
        f"/v1/approvals/{approval['approval_id']}/approve_once",
    )
    assert approved.status_code == 200
    session = _create_browser_session(client, approval_id=approval["approval_id"])

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over with a mobile-approved clearance."},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "user_controlling"
    audit = _audit_payloads(client, "handoff_engaged")[0]
    assert audit["channel"] == "mobile_signed"
    assert audit["risk_family"] == "external_effect"
    assert audit["clearance_ref"] == approval["approval_id"]
    consumed = client.app.state.store.get_approval(approval["approval_id"])
    assert consumed["decision_metadata"]["handoff_consumed_by"] == session["browser_session_id"]


def test_low_risk_browser_handoff_remains_capability_gated(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    session = _create_browser_session(client, approval_id=None, risk_family="read_only")

    response = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over a read-only browser view."},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "user_controlling"


def test_runtime_browser_handoff_high_risk_requires_bound_clearance(client: TestClient) -> None:
    paired = pair_device(client, requested_permissions=["read_state", "browser_assist"])
    client.app.state.store.upsert_agent(
        {
            "node_id": "node_test",
            "agent_id": "agent_mock",
            "display_name": "Mock Agent",
            "status": "idle",
            "capabilities": [{"name": "browser_assist", "status": "available"}],
        }
    )
    response = client.post(
        "/v1/runtime/browser-assistance/sessions",
        json={
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "reason": "Runtime browser takeover.",
            "risk_family": "external_effect",
            "context_redacted": {},
        },
    )
    assert response.status_code == 201
    session = response.json()

    engage = _signed(
        client,
        paired,
        "POST",
        f"/v1/browser-assistance/sessions/{session['browser_session_id']}/event",
        json_body={"note": "Taking over runtime browser handoff."},
    )

    assert engage.status_code == 403
    assert engage.json()["detail"] == "missing_clearance"


def test_handoff_contract_carries_risk_family() -> None:
    assert "risk_family" in RuntimeHandoffRequest.__dataclass_fields__
    assert "risk_family" in CreateAssistanceRequest.model_fields
    assert "risk_family" in CreateBrowserAssistanceSessionRequest.model_fields


def _create_browser_session(
    client: TestClient,
    *,
    approval_id: str | None,
    agent_id: str = "agent_mock",
    session_id: str = "sess_mock",
    risk_family: str = "external_effect",
) -> dict:
    response = client.post(
        "/v1/browser-assistance/sessions",
        json={
            "agent_id": agent_id,
            "session_id": session_id,
            "reason": "Browser submit needs human review.",
            "approval_id": approval_id,
            "risk_family": risk_family,
            "context_redacted": {"url": "https://example.invalid/form"},
        },
    )
    assert response.status_code == 201
    return response.json()


def _seed_approved_clearance(
    client: TestClient,
    *,
    metadata: dict,
    expires_at: str = "2099-01-01T00:00:00Z",
) -> dict:
    payload = {"operation": "submit_form"}
    approval = client.app.state.store.create_approval(
        {
            "approval_id": "appr_seeded_handoff",
            "action_id": "act_seeded_handoff",
            "node_id": "node_test",
            "agent_id": "agent_mock",
            "session_id": "sess_mock",
            "requested_tool": "browser_submit",
            "risk_level": "high",
            "risk_family": "external_effect",
            "risk_category": "browser",
            "summary": "Seeded approval.",
            "full_payload_redacted": payload,
            "payload_hash": content_hash(payload),
            "params_fingerprint": content_hash(payload),
            "resource_scope": None,
            "state": "pending",
            "options": ["approve_once", "deny"],
            "expires_at": expires_at,
        }
    )
    client.app.state.store.resolve_approval(
        approval["approval_id"],
        "approved",
        decision_scope="once",
        decision_actor_device_id="dev_seeded",
        decision_metadata=metadata,
    )
    return client.app.state.store.get_approval(approval["approval_id"])


def _audit_payloads(client: TestClient, event_type: str) -> list[dict]:
    return [
        event["payload_redacted"]
        for event in client.app.state.store.list_audit_events(event_type=event_type)
    ]


def _create_approval(
    client: TestClient,
    *,
    agent_id: str = "agent_mock",
    session_id: str = "sess_mock",
) -> dict:
    response = client.post(
        "/v1/hermes/tools/approval_requested",
        json={
            "requested_tool": "browser_submit",
            "risk_level": "high",
            "risk_family": "external_effect",
            "summary": "Submit a live browser form.",
            "payload_redacted": {"operation": "submit_form"},
            "agent_id": agent_id,
            "session_id": session_id,
            "expires_in_seconds": 300,
            "suggested_scopes": ["once"],
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
