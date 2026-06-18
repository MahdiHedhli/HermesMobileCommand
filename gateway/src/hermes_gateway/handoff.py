from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status

from .clearance_policy import ALL_RISK_FAMILIES, LOW_RISK_FAMILIES
from .config import Settings
from .security import now_utc, parse_utc, utc_iso
from .store import SQLiteStore


def engage_handoff(
    *,
    store: SQLiteStore,
    settings: Settings,
    handoff_kind: str,
    handoff_ref: str,
    node_id: str,
    agent_id: str,
    work_ref: str | None,
    risk_family: str,
    clearance_ref: str | None,
    request_id: str,
    actor_type: str,
    actor_id: str,
    params_fingerprint: str | None = None,
    engage: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    del settings
    normalized_risk_family = (
        risk_family if risk_family in ALL_RISK_FAMILIES else "external_effect"
    )
    clearance = None
    clearance_metadata: dict[str, Any] = {}
    if normalized_risk_family not in LOW_RISK_FAMILIES:
        clearance, clearance_metadata = _require_bound_clearance(
            store=store,
            handoff_kind=handoff_kind,
            handoff_ref=handoff_ref,
            node_id=node_id,
            agent_id=agent_id,
            work_ref=work_ref,
            risk_family=normalized_risk_family,
            clearance_ref=clearance_ref,
            request_id=request_id,
            actor_type=actor_type,
            actor_id=actor_id,
            params_fingerprint=params_fingerprint,
        )

    engaged = engage()
    engaged_ref = _engaged_ref(handoff_kind=handoff_kind, record=engaged) or handoff_ref
    if clearance is not None:
        store.update_approval_decision_metadata(
            clearance["approval_id"],
            {
                "handoff_consumed_by": engaged_ref,
                "handoff_consumed_at": utc_iso(),
                "handoff_kind": handoff_kind,
            },
        )
    store.append_audit_event(
        event_type="handoff_engaged",
        actor_type=actor_type,
        actor_id=actor_id,
        node_id=node_id,
        agent_id=agent_id,
        session_id=work_ref,
        approval_id=clearance_ref,
        request_id=request_id,
        payload_redacted={
            "handoff_kind": handoff_kind,
            "handoff_ref": handoff_ref,
            "engaged_ref": engaged_ref,
            "risk_family": normalized_risk_family,
            "clearance_ref": clearance_ref,
            "channel": clearance_metadata.get("channel"),
            "decision": "engaged",
            "eligibility_result": clearance_metadata.get("eligibility_result")
            or "not_required",
        },
    )
    return engaged


def _require_bound_clearance(
    *,
    store: SQLiteStore,
    handoff_kind: str,
    handoff_ref: str,
    node_id: str,
    agent_id: str,
    work_ref: str | None,
    risk_family: str,
    clearance_ref: str | None,
    request_id: str,
    actor_type: str,
    actor_id: str,
    params_fingerprint: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not clearance_ref:
        _reject(
            store=store,
            request_id=request_id,
            actor_type=actor_type,
            actor_id=actor_id,
            node_id=node_id,
            agent_id=agent_id,
            work_ref=work_ref,
            handoff_kind=handoff_kind,
            handoff_ref=handoff_ref,
            risk_family=risk_family,
            clearance_ref=clearance_ref,
            reason="missing_clearance",
        )
    try:
        approval = store.get_approval(clearance_ref)
    except KeyError:
        _reject(
            store=store,
            request_id=request_id,
            actor_type=actor_type,
            actor_id=actor_id,
            node_id=node_id,
            agent_id=agent_id,
            work_ref=work_ref,
            handoff_kind=handoff_kind,
            handoff_ref=handoff_ref,
            risk_family=risk_family,
            clearance_ref=clearance_ref,
            reason="clearance_not_found",
        )
    metadata = approval.get("decision_metadata") or {}
    checks = {
        "approved": approval.get("state") == "approved",
        "not_expired": parse_utc(approval["expires_at"]) > now_utc(),
        "not_consumed": not metadata.get("handoff_consumed_by")
        and not metadata.get("tui_consumed_by"),
        "same_node": approval.get("node_id") == node_id,
        "same_actor": approval.get("agent_id") == agent_id,
        "same_work": approval.get("session_id") == work_ref,
        "same_params": not params_fingerprint
        or approval.get("params_fingerprint") == params_fingerprint,
        "eligible": metadata.get("eligibility_result") == "allowed",
        "same_risk_family": metadata.get("risk_family") == risk_family,
        "channel_allowed": metadata.get("channel") in (metadata.get("eligible_channels") or []),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        _reject(
            store=store,
            request_id=request_id,
            actor_type=actor_type,
            actor_id=actor_id,
            node_id=node_id,
            agent_id=agent_id,
            work_ref=work_ref,
            handoff_kind=handoff_kind,
            handoff_ref=handoff_ref,
            risk_family=risk_family,
            clearance_ref=clearance_ref,
            reason=failed[0],
        )
    return approval, metadata


def _reject(
    *,
    store: SQLiteStore,
    request_id: str,
    actor_type: str,
    actor_id: str,
    node_id: str,
    agent_id: str,
    work_ref: str | None,
    handoff_kind: str,
    handoff_ref: str,
    risk_family: str,
    clearance_ref: str | None,
    reason: str,
) -> None:
    store.append_audit_event(
        event_type="handoff_engage_rejected",
        actor_type=actor_type,
        actor_id=actor_id,
        node_id=node_id,
        agent_id=agent_id,
        session_id=work_ref,
        approval_id=clearance_ref,
        request_id=request_id,
        payload_redacted={
            "handoff_kind": handoff_kind,
            "handoff_ref": handoff_ref,
            "risk_family": risk_family,
            "clearance_ref": clearance_ref,
            "decision": "rejected",
            "eligibility_result": "rejected",
            "reason": reason,
        },
    )
    raise HTTPException(status.HTTP_403_FORBIDDEN, reason)


def _engaged_ref(*, handoff_kind: str, record: dict[str, Any]) -> str | None:
    if handoff_kind == "operator_guidance":
        return record.get("assistance_session_id")
    if handoff_kind == "browser_review":
        return record.get("browser_session_id")
    if handoff_kind == "voice_prompt":
        return record.get("voice_session_id")
    return None
