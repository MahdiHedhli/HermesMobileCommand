from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from .capabilities import require_runtime_capability
from .config import Settings
from .ids import new_id
from .schemas import (
    ApprovalRequest,
    ApprovalResponse,
    BrowserAssistanceSession,
    CreateAssistanceRequest,
    CreateBrowserAssistanceSessionRequest,
    HermesApprovalRequestedRequest,
    Mission,
    MobileNotifyRequest,
    Notification,
    RuntimeApprovalResult,
    RuntimeBrowserAssistanceResult,
    RuntimeContextRequest,
    RuntimeContextResponse,
    RuntimeCreateVoiceSessionRequest,
    RuntimeTuaResult,
    RuntimeVoiceResult,
    VoiceSession,
)
from .security import expires_in, has_secret_text, now_utc, parse_utc
from .store import SQLiteStore

MAX_NOTIFICATION_TITLE_CHARS = 120
MAX_NOTIFICATION_BODY_CHARS = 800


@dataclass(frozen=True)
class HermesRuntimeAdapter:
    store: SQLiteStore
    settings: Settings

    def register_context(
        self,
        *,
        payload: RuntimeContextRequest,
        request_id: str,
    ) -> RuntimeContextResponse:
        node_id = payload.node_id or self.settings.node_id
        existing_agent = self._existing_agent(node_id, payload.agent_id)
        agent = self.store.upsert_agent(
            {
                "agent_id": payload.agent_id,
                "node_id": node_id,
                "display_name": payload.display_name
                or existing_agent.get("display_name")
                or payload.agent_id,
                "agent_kind": existing_agent.get("agent_kind") or "primary",
                "status": payload.agent_status,
                "active_session_id": payload.session_id,
                "current_tool": payload.current_tool,
                "current_target": payload.current_target,
                "tags": existing_agent.get("tags", []),
                "capabilities": [item.model_dump() for item in payload.capabilities]
                or existing_agent.get("capabilities", []),
            }
        )
        session = None
        if payload.session_id:
            session = self.store.upsert_session(
                {
                    "session_id": payload.session_id,
                    "node_id": node_id,
                    "agent_id": payload.agent_id,
                    "status": _session_status_from_mission(payload.mission_state),
                    "title": payload.mission_title,
                    "summary": payload.mission_summary,
                    "current_tool": payload.current_tool,
                    "current_target": payload.current_target,
                }
            )
        mission = None
        if payload.mission_id:
            mission = self.store.upsert_mission(
                {
                    "mission_id": payload.mission_id,
                    "node_id": node_id,
                    "agent_id": payload.agent_id,
                    "session_id": payload.session_id,
                    "state": payload.mission_state,
                    "title": payload.mission_title,
                    "summary": payload.mission_summary,
                }
            )
            self.store.create_event(
                node_id=node_id,
                agent_id=payload.agent_id,
                session_id=payload.session_id,
                event_type="mission.state",
                payload={
                    "mission_id": payload.mission_id,
                    "state": payload.mission_state,
                },
            )
        self.store.append_audit_event(
            event_type="runtime_context_registered",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            request_id=request_id,
            payload_redacted={
                "mission_id": payload.mission_id,
                "agent_status": payload.agent_status,
                "mission_state": payload.mission_state,
            },
        )
        self.store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="agent.status",
            payload={"agent_id": payload.agent_id, "status": payload.agent_status},
        )
        return RuntimeContextResponse(
            agent=agent,
            mission=Mission.model_validate(mission) if mission else None,
            session=session,
        )

    def create_notification(
        self,
        *,
        payload: MobileNotifyRequest,
        request_id: str,
    ) -> Notification:
        rejection_reason = _notification_rejection_reason(payload)
        if rejection_reason:
            self.store.append_audit_event(
                event_type="notification_rejected",
                actor_type="hermes",
                actor_id=payload.agent_id,
                node_id=self.settings.node_id,
                agent_id=payload.agent_id,
                session_id=payload.session_id,
                request_id=request_id,
                payload_redacted={"category": payload.category, "reason": rejection_reason},
            )
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "notification body is not safe",
            )
        notification = self.store.create_notification(
            {
                "node_id": self.settings.node_id,
                "agent_id": payload.agent_id,
                "session_id": payload.session_id,
                "action_id": payload.action_id,
                "category": payload.category,
                "urgency": payload.urgency,
                "title_safe": payload.title,
                "body_safe": payload.body,
                "dedupe_key": payload.dedupe_key,
                "state": "queued",
            }
        )
        self.store.append_audit_event(
            event_type="notification_queued",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=self.settings.node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            notification_id=notification["notification_id"],
            request_id=request_id,
            payload_redacted={"category": payload.category, "urgency": payload.urgency},
        )
        self.store.create_event(
            node_id=self.settings.node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="notification.created",
            payload={
                "notification_id": notification["notification_id"],
                "category": payload.category,
                "urgency": payload.urgency,
            },
        )
        return Notification.model_validate(notification)

    def request_approval(
        self,
        *,
        payload: HermesApprovalRequestedRequest,
        request_id: str,
    ) -> ApprovalRequest:
        node_id = payload.node_id or self.settings.node_id
        approval_id = new_id("appr")
        approval = self.store.create_approval(
            {
                "approval_id": approval_id,
                "action_id": payload.action_id or new_id("act"),
                "node_id": node_id,
                "agent_id": payload.agent_id,
                "session_id": payload.session_id,
                "requested_tool": payload.requested_tool,
                "risk_level": payload.risk_level,
                "risk_category": payload.risk_category or "unknown_action",
                "summary": payload.summary,
                "full_payload_redacted": payload.payload_redacted,
                "resource_scope": payload.resource_scope,
                "state": "pending",
                "options": _approval_options_from_scopes(payload.suggested_scopes),
                "expires_at": expires_in(payload.expires_in_seconds).isoformat(),
            }
        )
        self._set_agent_runtime_state(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            status="waiting_approval",
            current_tool=payload.requested_tool,
        )
        self.store.append_audit_event(
            event_type="approval_requested",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            approval_id=approval_id,
            request_id=request_id,
            payload_redacted={
                "requested_tool": payload.requested_tool,
                "risk_level": payload.risk_level,
                "risk_category": payload.risk_category or "unknown_action",
            },
        )
        self.store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="approval.requested",
            payload={
                "approval_id": approval_id,
                "state": "pending",
                "risk_level": payload.risk_level,
            },
        )
        return ApprovalRequest.model_validate(approval)

    def approval_result(self, approval_id: str) -> RuntimeApprovalResult:
        self.expire_pending_approvals()
        try:
            approval = self.store.get_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
        responses = [
            ApprovalResponse.model_validate(response)
            for response in self.store.list_approval_responses(approval_id)
        ]
        return RuntimeApprovalResult(
            approval_id=approval["approval_id"],
            state=approval["state"],
            selected_scope=approval["decision_scope"]
            if approval["state"] == "approved"
            else None,
            decided_at=approval["decided_at"],
            decision_metadata=approval["decision_metadata"] or {},
            responses=responses,
        )

    def cancel_approval(
        self,
        *,
        approval_id: str,
        request_id: str,
        actor_id: str,
    ) -> RuntimeApprovalResult:
        try:
            approval = self.store.get_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
        if approval["state"] == "pending":
            self.store.resolve_approval(
                approval_id,
                "cancelled",
                decision_metadata={"reason": "runtime_cancelled"},
            )
            self.store.append_audit_event(
                event_type="approval_cancelled",
                actor_type="hermes",
                actor_id=actor_id,
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                approval_id=approval_id,
                request_id=request_id,
                payload_redacted={"reason": "runtime_cancelled"},
            )
            self.store.create_event(
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                event_type="approval.resolved",
                payload={"approval_id": approval_id, "state": "cancelled"},
            )
        return self.approval_result(approval_id)

    def expire_pending_approvals(self) -> None:
        for approval in self.store.list_approvals(state="pending"):
            if parse_utc(approval["expires_at"]) > now_utc():
                continue
            self.store.resolve_approval(
                approval["approval_id"],
                "expired",
                decision_metadata={"reason": "runtime_result_poll"},
            )
            request_id = new_id("req")
            self.store.append_audit_event(
                event_type="approval_expired",
                actor_type="gateway",
                actor_id="gateway",
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                approval_id=approval["approval_id"],
                request_id=request_id,
                payload_redacted={"reason": "runtime_result_poll"},
            )
            self.store.create_event(
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                event_type="approval.resolved",
                payload={"approval_id": approval["approval_id"], "state": "expired"},
            )

    def create_tua_request(
        self,
        *,
        payload: CreateAssistanceRequest,
        request_id: str,
        actor_id: str,
    ) -> Any:
        node_id = payload.node_id or self.settings.node_id
        require_runtime_capability(
            store=self.store,
            settings=self.settings,
            capability="tua",
            request_id=request_id,
            actor_id=actor_id,
            node_id=node_id,
            agent_id=payload.agent_id,
        )
        assistance_request = self.store.create_assistance_request(
            {
                "node_id": node_id,
                "agent_id": payload.agent_id,
                "session_id": payload.session_id,
                "approval_id": payload.approval_id,
                "reason": payload.reason,
                "state": "requested",
                "context_redacted": payload.context_redacted,
            }
        )
        self._set_agent_runtime_state(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            status="waiting_assistance",
        )
        self.store.append_audit_event(
            event_type="tua_request_created",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            request_id=request_id,
            payload_redacted={"request_id": assistance_request["request_id"]},
        )
        self.store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="tua.requested",
            payload={"request_id": assistance_request["request_id"]},
        )
        return assistance_request

    def tua_result(self, request_id: str) -> RuntimeTuaResult:
        try:
            request = self.store.get_assistance_request(request_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "TUA request not found") from exc
        sessions = self.store.list_assistance_sessions(request_id=request_id)
        latest = sessions[0] if sessions else None
        return RuntimeTuaResult(
            request=request,
            sessions=sessions,
            latest_session=latest,
            return_summary=latest.get("return_summary") if latest else None,
        )

    def create_browser_assistance_session(
        self,
        *,
        payload: CreateBrowserAssistanceSessionRequest,
        request_id: str,
        actor_id: str,
    ) -> BrowserAssistanceSession:
        node_id = payload.node_id or self.settings.node_id
        require_runtime_capability(
            store=self.store,
            settings=self.settings,
            capability="browser_assistance",
            request_id=request_id,
            actor_id=actor_id,
            node_id=node_id,
            agent_id=payload.agent_id,
        )
        session = self.store.create_browser_assistance_session(
            {
                "node_id": node_id,
                "agent_id": payload.agent_id,
                "session_id": payload.session_id,
                "approval_id": payload.approval_id,
                "reason": payload.reason,
                "state": "requested",
                "context_redacted": payload.context_redacted,
            }
        )
        self.store.create_operator_session(
            {
                "session_id": session["browser_session_id"],
                "session_type": "browser_assistance",
                "agent_id": payload.agent_id,
                "mission_id": _mission_id_from_context(payload.context_redacted),
                "state": "requested",
                "capability_requirements": ["browser_assistance"],
                "context": payload.context_redacted,
            }
        )
        self._set_agent_runtime_state(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            status="waiting_assistance",
        )
        self.store.append_audit_event(
            event_type="browser_assistance_requested",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            request_id=request_id,
            payload_redacted={"browser_session_id": session["browser_session_id"]},
        )
        self.store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="browser_assistance.requested",
            payload={"browser_session_id": session["browser_session_id"]},
        )
        return BrowserAssistanceSession.model_validate(session)

    def browser_result(self, session_id: str) -> RuntimeBrowserAssistanceResult:
        try:
            session = self.store.get_browser_assistance_session(session_id)
        except KeyError as exc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "browser assistance session not found",
            ) from exc
        return RuntimeBrowserAssistanceResult(
            session=session,
            return_summary=session.get("return_summary"),
        )

    def create_voice_session(
        self,
        *,
        payload: RuntimeCreateVoiceSessionRequest,
        request_id: str,
        actor_id: str,
    ) -> VoiceSession:
        node_id = payload.node_id or self.settings.node_id
        require_runtime_capability(
            store=self.store,
            settings=self.settings,
            capability="voice",
            request_id=request_id,
            actor_id=actor_id,
            node_id=node_id,
            agent_id=payload.agent_id,
        )
        session = self.store.create_voice_session(
            {
                "node_id": node_id,
                "agent_id": payload.agent_id,
                "session_id": payload.session_id,
                "created_by_device_id": f"runtime:{actor_id}",
                "mode": payload.mode,
                "state": "active",
            }
        )
        self.store.create_operator_session(
            {
                "session_id": session["voice_session_id"],
                "session_type": "voice",
                "agent_id": payload.agent_id,
                "mission_id": _mission_id_from_context(payload.context_redacted),
                "state": "active",
                "capability_requirements": ["voice"],
                "context": payload.context_redacted,
            }
        )
        self.store.append_audit_event(
            event_type="voice_session_created",
            actor_type="hermes",
            actor_id=actor_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            voice_session_id=session["voice_session_id"],
            request_id=request_id,
            payload_redacted={"mode": payload.mode, "runtime_created": True},
        )
        self.store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="voice.session.created",
            payload={"voice_session_id": session["voice_session_id"], "mode": payload.mode},
        )
        return VoiceSession.model_validate(session)

    def voice_result(self, session_id: str) -> RuntimeVoiceResult:
        try:
            session = self.store.get_voice_session(session_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "voice session not found") from exc
        return RuntimeVoiceResult(session=session, messages=session["messages"])

    def _set_agent_runtime_state(
        self,
        *,
        node_id: str,
        agent_id: str,
        session_id: str | None,
        status: str,
        current_tool: str | None = None,
    ) -> None:
        existing = self._existing_agent(node_id, agent_id)
        self.store.upsert_agent(
            {
                "agent_id": agent_id,
                "node_id": node_id,
                "display_name": existing.get("display_name") or agent_id,
                "agent_kind": existing.get("agent_kind") or "primary",
                "status": status,
                "active_session_id": session_id,
                "current_tool": current_tool or existing.get("current_tool"),
                "current_target": existing.get("current_target"),
                "tags": existing.get("tags", []),
                "capabilities": existing.get("capabilities", []),
            }
        )
        self.store.create_event(
            node_id=node_id,
            agent_id=agent_id,
            session_id=session_id,
            event_type="agent.status",
            payload={"agent_id": agent_id, "status": status},
        )

    def _existing_agent(self, node_id: str, agent_id: str) -> dict[str, Any]:
        try:
            return self.store.get_agent(node_id, agent_id)
        except KeyError:
            return {}


def _notification_rejection_reason(payload: MobileNotifyRequest) -> str | None:
    if len(payload.title) > MAX_NOTIFICATION_TITLE_CHARS:
        return "title_too_large"
    if len(payload.body) > MAX_NOTIFICATION_BODY_CHARS:
        return "body_too_large"
    if has_secret_text(payload.title, payload.body):
        return "secret_scan_failed"
    return None


def _approval_options_from_scopes(scopes: list[str]) -> list[str]:
    scope_options = {
        "once": "approve_once",
        "session": "approve_for_session",
        "agent": "approve_for_agent",
        "permanent": "approve_permanent",
    }
    options = [scope_options[scope] for scope in scopes if scope in scope_options]
    return [*options, "deny"] if options else ["deny"]


def _session_status_from_mission(mission_state: str) -> str:
    if mission_state in {"completed", "cancelled", "failed"}:
        return {"completed": "completed", "cancelled": "cancelled", "failed": "failed"}[
            mission_state
        ]
    if mission_state in {"waiting_approval", "waiting_assistance", "user_controlling"}:
        return "blocked"
    return "active"


def _mission_id_from_context(context: dict[str, Any]) -> str | None:
    value = context.get("mission_id")
    return value if isinstance(value, str) and value else None
