from __future__ import annotations

import pytest
from pydantic import ValidationError

from hermes_gateway.schemas import (
    Agent,
    ApprovalRequest,
    AuditEvent,
    Device,
    MobileNotifyRequest,
    Notification,
    Session,
)
from hermes_gateway.security import now_utc


def test_required_models_validate() -> None:
    now = now_utc()
    Agent(
        agent_id="agent_1",
        node_id="node_1",
        display_name="Agent",
        status="idle",
        capabilities=[],
    )
    Device(
        device_id="dev_1",
        node_id="node_1",
        device_name="Phone",
        platform="ios",
        status="active",
        permissions=["read_state"],
        registered_at=now,
    )
    Session(
        session_id="sess_1",
        node_id="node_1",
        agent_id="agent_1",
        status="active",
        started_at=now,
    )
    ApprovalRequest(
        approval_id="appr_1",
        action_id="act_1",
        node_id="node_1",
        agent_id="agent_1",
        session_id="sess_1",
            requested_tool="shell",
            risk_level="high",
            risk_family="destructive",
            params_fingerprint="fp_test",
            summary="Run command",
        full_payload_redacted={"command": "redacted"},
        state="pending",
        expires_at=now,
        options=["approve_once", "deny"],
    )
    Notification(
        notification_id="ntf_1",
        node_id="node_1",
        agent_id="agent_1",
        session_id="sess_1",
        category="approval_required",
        urgency="high",
        state="queued",
        created_at=now,
    )
    AuditEvent(
        audit_event_id="aud_1",
        event_type="notification_queued",
        actor_type="gateway",
        actor_id="gateway",
        node_id="node_1",
        request_id="req_1",
        previous_hash=None,
        hash="hash",
        created_at=now,
    )


def test_invalid_notification_category_rejected() -> None:
    with pytest.raises(ValidationError):
        MobileNotifyRequest(
            title="Bad",
            body="Bad",
            urgency="high",
            category="task_blocked",
            agent_id="agent_1",
            session_id="sess_1",
        )
