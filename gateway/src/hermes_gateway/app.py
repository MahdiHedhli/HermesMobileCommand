from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from .capabilities import require_device_capability, require_runtime_capability
from .clearance_policy import (
    authority_from_channel,
    channel_for_device,
    channel_satisfies,
    required_channels_for_risk_vector,
)
from .config import Settings
from .ids import new_id
from .local_binding import HermesLocalCaller, verify_hermes_local_request
from .runtime_adapter import (
    HermesRuntimeAdapter,
    RuntimeAdapter,
    RuntimeClearanceRequest,
    RuntimeHandoffRequest,
    RuntimeNotice,
    RuntimeWorkState,
)
from .schemas import (
    Agent,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalPolicyProposal,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatusRequest,
    ApprovalStatusResponse,
    AssistanceMessage,
    AssistanceRequest,
    AssistanceSession,
    AuthTokenSet,
    BrowserAssistanceEventRequest,
    BrowserAssistanceSession,
    CompletePairingRequest,
    CompletePairingResponse,
    CreateApprovalRequest,
    CreateApprovalResponseRequest,
    CreateAssistanceMessageRequest,
    CreateAssistanceRequest,
    CreateAssistanceSessionRequest,
    CreateBrowserAssistanceSessionRequest,
    CreatePairingSessionRequest,
    CreateTuiSessionRequest,
    CreateVoiceMessageRequest,
    CreateVoiceSessionRequest,
    Device,
    GatewayHealth,
    HermesApprovalRequestedRequest,
    InterventionRequest,
    InterventionResponse,
    Inventory,
    Mission,
    MobileNotifyRequest,
    Node,
    NodeRegistration,
    Notification,
    OperatorSession,
    PairingSession,
    RefreshTokenRequest,
    ReturnControlRequest,
    RuntimeApprovalResult,
    RuntimeBrowserAssistanceResult,
    RuntimeContextRequest,
    RuntimeContextResponse,
    RuntimeCreateVoiceSessionRequest,
    RuntimeTuaResult,
    RuntimeVoiceResult,
    TuiAttachTokenResponse,
    TuiSession,
    TuiSessionControlResponse,
    VoiceMessage,
    VoiceSession,
)
from .security import compare_token, expires_in, has_secret_text, new_token, now_utc, parse_utc
from .signing import VerifiedDevice, verify_signed_request
from .store import SQLiteStore
from .tui import LocalPtyManager, validate_tui_frame, validate_tui_request

DEFAULT_PERMISSIONS = ["read_state", "chat", "approve", "intervene"]
MAX_NOTIFICATION_TITLE_CHARS = 120
MAX_NOTIFICATION_BODY_CHARS = 800


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    store = SQLiteStore(resolved_settings.database_path)
    store.initialize()
    _ensure_local_node(store, resolved_settings)
    store.seed_mock_data(node_id=resolved_settings.node_id)
    tui_manager = LocalPtyManager(store=store, settings=resolved_settings)
    runtime_adapter: RuntimeAdapter = HermesRuntimeAdapter(
        store=store,
        settings=resolved_settings,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await tui_manager.close_all()

    app = FastAPI(
        title="Agentic Control Tower Gateway",
        version=resolved_settings.gateway_version,
        description="Self-hosted control tower gateway for agentic backends.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.store = store
    app.state.tui_manager = tui_manager
    app.state.runtime_adapter = runtime_adapter
    if resolved_settings.cors_allowed_origin_regex:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=resolved_settings.cors_allowed_origin_regex,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    async def require_signed_device(request: Request) -> VerifiedDevice:
        return await verify_signed_request(request, store=store, settings=resolved_settings)

    def require_hermes_local_request(request: Request) -> HermesLocalCaller:
        return verify_hermes_local_request(
            request,
            store=store,
            settings=resolved_settings,
        )

    signed_device_dependency = Depends(require_signed_device)
    hermes_local_dependency = Depends(require_hermes_local_request)

    @app.get("/v1/health", response_model=GatewayHealth)
    def health() -> GatewayHealth:
        return GatewayHealth(
            node_id=resolved_settings.node_id,
            status="healthy",
            gateway_version=resolved_settings.gateway_version,
            hermes_version=resolved_settings.hermes_version,
            checked_at=now_utc(),
            services={
                "database": "healthy",
                "pairing": "healthy",
                "event_stream": "healthy",
                "push_dispatch": "unavailable",
                "tui_pty": "healthy"
                if resolved_settings.tui_enable_local_pty
                else "unavailable",
            },
        )

    @app.post("/v1/nodes/register", response_model=Node, status_code=status.HTTP_201_CREATED)
    def register_node(
        payload: NodeRegistration,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> Node:
        node_id = payload.node_id or resolved_settings.node_id
        node = store.upsert_node(
            {
                "node_id": node_id,
                "display_name": payload.display_name,
                "environment": payload.environment,
                "gateway_base_url": payload.gateway_base_url,
                "node_fingerprint": payload.node_fingerprint,
                "gateway_version": payload.gateway_version,
                "hermes_version": payload.hermes_version,
                "health": "online",
                "tags": payload.tags,
            }
        )
        store.append_audit_event(
            event_type="node_registered",
            actor_type="gateway",
            actor_id="gateway",
            node_id=node_id,
            request_id=_request_id(request),
            payload_redacted={"display_name": payload.display_name},
        )
        store.create_event(
            node_id=node_id,
            event_type="system.health",
            payload={"status": "healthy", "reason": "node_registered"},
        )
        return Node.model_validate(node)

    @app.get("/v1/inventory", response_model=Inventory)
    def inventory(_device: VerifiedDevice = signed_device_dependency) -> Inventory:
        return Inventory(nodes=[Node.model_validate(node) for node in store.list_nodes()])

    @app.get("/v1/nodes/{node_id}", response_model=Node)
    def get_node(
        node_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> Node:
        try:
            return Node.model_validate(store.get_node(node_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "node not found") from exc

    @app.get("/v1/agents")
    def list_agents(
        node_id: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[Agent]]:
        return {"agents": [Agent.model_validate(agent) for agent in store.list_agents(node_id)]}

    @app.get("/v1/agents/{agent_id}", response_model=Agent)
    def get_agent(
        agent_id: str,
        node_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> Agent:
        try:
            return Agent.model_validate(store.get_agent(node_id, agent_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "agent not found") from exc

    @app.get("/v1/sessions")
    def list_sessions(
        node_id: str | None = None,
        agent_id: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[dict[str, Any]]]:
        return {"sessions": store.list_sessions(node_id=node_id, agent_id=agent_id)}

    @app.get("/v1/sessions/{session_id}")
    def get_session(
        session_id: str,
        node_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, Any]:
        try:
            return store.get_session(node_id, session_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from exc

    @app.get("/v1/sessions/{session_id}/activity")
    def get_session_activity(
        session_id: str,
        node_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, Any]:
        try:
            session = store.get_session(node_id, session_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found") from exc
        events = [
            event
            for event in store.list_events_after(limit=25)
            if event.get("node_id") == node_id and event.get("session_id") == session_id
        ]
        return {
            "session": session,
            "recent_events": events,
            "terminal_tail": None,
            "browser_state": None,
        }

    @app.get("/v1/missions")
    def list_missions(
        node_id: str | None = None,
        agent_id: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[Mission]]:
        return {
            "missions": [
                Mission.model_validate(mission)
                for mission in store.list_missions(node_id=node_id, agent_id=agent_id)
            ]
        }

    @app.get("/v1/missions/{mission_id}", response_model=Mission)
    def get_mission(
        mission_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> Mission:
        try:
            return Mission.model_validate(store.get_mission(mission_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "mission not found") from exc

    @app.post("/v1/runtime/context", response_model=RuntimeContextResponse)
    def runtime_register_context(
        payload: RuntimeContextRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> RuntimeContextResponse:
        return runtime_adapter.record_work_state(
            RuntimeWorkState(
                actor_ref=payload.agent_id,
                display_name=payload.display_name,
                state=payload.agent_status,
                unit_ref=payload.mission_id,
                unit_state=payload.mission_state,
                work_ref=payload.session_id,
                unit_title=payload.mission_title,
                unit_summary=payload.mission_summary,
                operation=payload.current_tool,
                target=payload.current_target,
                node_ref=payload.node_id,
                capabilities=[capability.model_dump() for capability in payload.capabilities],
            ),
            request_id=_request_id(request),
        )

    @app.post(
        "/v1/runtime/notifications",
        response_model=Notification,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def runtime_notification(
        payload: MobileNotifyRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> Notification:
        require_runtime_capability(
            store=store,
            settings=resolved_settings,
            capability="notifications",
            request_id=_request_id(request),
            actor_id=payload.agent_id,
            agent_id=payload.agent_id,
        )
        result = runtime_adapter.publish_notice(
            RuntimeNotice(
                title=payload.title,
                body=payload.body,
                urgency=payload.urgency,
                category=payload.category,
                actor_ref=payload.agent_id,
                work_ref=payload.session_id,
                action_ref=payload.action_id,
                deep_link=payload.deep_link,
            ),
            request_id=_request_id(request),
        )
        return result.raw

    @app.post(
        "/v1/runtime/approvals",
        response_model=ApprovalRequest,
        status_code=status.HTTP_201_CREATED,
    )
    def runtime_approval_requested(
        payload: HermesApprovalRequestedRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalRequest:
        require_runtime_capability(
            store=store,
            settings=resolved_settings,
            capability="approvals",
            request_id=_request_id(request),
            actor_id=payload.agent_id,
            node_id=payload.node_id,
            agent_id=payload.agent_id,
        )
        result = runtime_adapter.request_clearance(
            RuntimeClearanceRequest(
                operation=payload.requested_tool,
                risk_level=payload.risk_level,
                summary=payload.summary,
                payload_redacted=payload.payload_redacted,
                actor_ref=payload.agent_id,
                work_ref=payload.session_id,
                expires_in_seconds=payload.expires_in_seconds,
                scopes=payload.suggested_scopes,
                action_ref=payload.action_id,
                node_ref=payload.node_id,
                risk_category=payload.risk_category,
                resource_scope=payload.resource_scope,
            ),
            request_id=_request_id(request),
        )
        return result.raw

    @app.get("/v1/runtime/approvals/{approval_id}/result", response_model=RuntimeApprovalResult)
    def runtime_approval_result(
        approval_id: str,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> RuntimeApprovalResult:
        return runtime_adapter.check_clearance(approval_id).raw

    @app.post("/v1/runtime/approvals/{approval_id}/cancel", response_model=RuntimeApprovalResult)
    def runtime_cancel_approval(
        approval_id: str,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> RuntimeApprovalResult:
        return runtime_adapter.cancel_clearance(
            approval_id,
            request_id=_request_id(request),
            actor_ref="runtime",
        ).raw

    @app.post(
        "/v1/runtime/approvals/{approval_id}/reserve",
        response_model=ApprovalRequest,
    )
    def runtime_reserve_approval(
        approval_id: str,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalRequest:
        # Change 3 — two-phase consume, phase 1. Reserve an approved clearance at
        # validation; only one consumer can hold it (atomic state guard).
        try:
            approval = store.reserve_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        store.append_audit_event(
            event_type="approval_reserved",
            actor_type="runtime",
            actor_id="runtime",
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            approval_id=approval_id,
            request_id=_request_id(request),
            payload_redacted={"state": "reserved"},
        )
        return ApprovalRequest.model_validate(approval)

    @app.post(
        "/v1/runtime/approvals/{approval_id}/commit",
        response_model=ApprovalRequest,
    )
    def runtime_commit_approval(
        approval_id: str,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalRequest:
        # Change 3 — two-phase consume, phase 2. Commit only from reserved,
        # preserving one-time consumption.
        try:
            approval = store.commit_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        store.append_audit_event(
            event_type="approval_committed",
            actor_type="runtime",
            actor_id="runtime",
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            approval_id=approval_id,
            request_id=_request_id(request),
            payload_redacted={"state": "committed"},
        )
        return ApprovalRequest.model_validate(approval)

    @app.post(
        "/v1/runtime/approvals/{approval_id}/release",
        response_model=ApprovalRequest,
    )
    def runtime_release_approval(
        approval_id: str,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalRequest:
        # Change 3 — two-phase consume, symmetric inverse of commit. Release a
        # reserved clearance back to cancelled (only from reserved), so a
        # reserved-but-not-executed clearance never dangles. Fail-closed: 404 if
        # missing, 409 if not reserved; one-time consumption preserved.
        try:
            approval = store.release_approval(approval_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        store.append_audit_event(
            event_type="approval_released",
            actor_type="runtime",
            actor_id="runtime",
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            approval_id=approval_id,
            request_id=_request_id(request),
            payload_redacted={"state": "cancelled"},
        )
        return ApprovalRequest.model_validate(approval)

    @app.post(
        "/v1/runtime/tua/requests",
        response_model=AssistanceRequest,
        status_code=status.HTTP_201_CREATED,
    )
    def runtime_tua_request(
        payload: CreateAssistanceRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> AssistanceRequest:
        result = runtime_adapter.request_handoff(
            RuntimeHandoffRequest(
                handoff_kind="operator_guidance",
                actor_ref=payload.agent_id,
                work_ref=payload.session_id,
                reason=payload.reason,
                node_ref=payload.node_id,
                clearance_ref=payload.approval_id,
                context_redacted=payload.context_redacted,
            ),
            request_id=_request_id(request),
            actor_ref=payload.agent_id,
        )
        return AssistanceRequest.model_validate(result.raw)

    @app.get("/v1/runtime/tua/requests/{request_id}/result", response_model=RuntimeTuaResult)
    def runtime_tua_result(
        request_id: str,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> RuntimeTuaResult:
        return runtime_adapter.check_handoff("operator_guidance", request_id).raw

    @app.post(
        "/v1/runtime/browser-assistance/sessions",
        response_model=BrowserAssistanceSession,
        status_code=status.HTTP_201_CREATED,
    )
    def runtime_browser_assistance_session(
        payload: CreateBrowserAssistanceSessionRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> BrowserAssistanceSession:
        return runtime_adapter.request_handoff(
            RuntimeHandoffRequest(
                handoff_kind="browser_review",
                actor_ref=payload.agent_id,
                work_ref=payload.session_id,
                reason=payload.reason,
                node_ref=payload.node_id,
                clearance_ref=payload.approval_id,
                context_redacted=payload.context_redacted,
            ),
            request_id=_request_id(request),
            actor_ref=payload.agent_id,
        ).raw

    @app.get(
        "/v1/runtime/browser-assistance/sessions/{session_id}/result",
        response_model=RuntimeBrowserAssistanceResult,
    )
    def runtime_browser_assistance_result(
        session_id: str,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> RuntimeBrowserAssistanceResult:
        return runtime_adapter.check_handoff("browser_review", session_id).raw

    @app.post(
        "/v1/runtime/voice/sessions",
        response_model=VoiceSession,
        status_code=status.HTTP_201_CREATED,
    )
    def runtime_voice_session(
        payload: RuntimeCreateVoiceSessionRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> VoiceSession:
        return runtime_adapter.request_handoff(
            RuntimeHandoffRequest(
                handoff_kind="voice_prompt",
                actor_ref=payload.agent_id,
                work_ref=payload.session_id,
                reason="Runtime requested a voice prompt.",
                node_ref=payload.node_id,
                context_redacted=payload.context_redacted,
                mode=payload.mode,
            ),
            request_id=_request_id(request),
            actor_ref=payload.agent_id,
        ).raw

    @app.get("/v1/runtime/voice/sessions/{session_id}/result", response_model=RuntimeVoiceResult)
    def runtime_voice_result(
        session_id: str,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> RuntimeVoiceResult:
        return runtime_adapter.check_handoff("voice_prompt", session_id).raw

    @app.post(
        "/v1/pairing/start",
        response_model=PairingSession,
        status_code=status.HTTP_201_CREATED,
    )
    @app.post(
        "/v1/pairing/sessions", response_model=PairingSession, status_code=status.HTTP_201_CREATED
    )
    def start_pairing(payload: CreatePairingSessionRequest, request: Request) -> PairingSession:
        ttl_seconds = (
            payload.ttl_seconds
            if payload.ttl_seconds is not None
            else resolved_settings.pairing_ttl_seconds
        )
        pairing_token = new_token()
        pairing = store.create_pairing_session(
            node_id=resolved_settings.node_id,
            node_fingerprint=resolved_settings.node_fingerprint,
            display_name=payload.display_name,
            requested_permissions=payload.requested_permissions,
            pairing_token=pairing_token,
            challenge=new_token(),
            ttl_seconds=ttl_seconds,
        )
        store.append_audit_event(
            event_type="pairing_started",
            actor_type="gateway",
            actor_id="gateway",
            node_id=resolved_settings.node_id,
            request_id=_request_id(request),
            payload_redacted={"pairing_id": pairing["pairing_id"]},
        )
        return PairingSession.model_validate(pairing)

    @app.get("/v1/pairing/sessions/{pairing_id}", response_model=PairingSession)
    def get_pairing(pairing_id: str) -> PairingSession:
        try:
            pairing = store.get_pairing_session(pairing_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "pairing session not found") from exc
        return PairingSession.model_validate(_expire_pairing_if_needed(store, pairing))

    @app.post("/v1/pairing/complete", response_model=CompletePairingResponse)
    def complete_pairing(
        payload: CompletePairingRequest, request: Request
    ) -> CompletePairingResponse:
        try:
            pairing = store.get_pairing_session(payload.pairing_id, include_token=True)
        except KeyError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid pairing token") from exc

        pairing = _expire_pairing_if_needed(store, pairing)
        if pairing["status"] != "pending":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"pairing session is {pairing['status']}",
            )
        if not compare_token(payload.challenge_response, pairing["pairing_token_hash"]):
            store.append_audit_event(
                event_type="pairing_rejected",
                actor_type="gateway",
                actor_id="gateway",
                node_id=pairing["node_id"],
                request_id=_request_id(request),
                payload_redacted={"pairing_id": pairing["pairing_id"], "reason": "invalid_token"},
            )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid pairing token")

        permissions = pairing["requested_permissions"] or DEFAULT_PERMISSIONS
        device = store.create_device(
            node_id=pairing["node_id"],
            device_name=payload.device.device_name,
            platform=payload.device.platform,
            app_instance_id=payload.device.app_instance_id,
            app_version=payload.device.app_version,
            device_public_key=payload.device_public_key,
            permissions=permissions,
        )
        access_token = new_token()
        refresh_token = new_token()
        store.create_auth_token(
            token=access_token,
            token_type="access",
            device_id=device["device_id"],
            ttl_seconds=15 * 60,
        )
        store.create_auth_token(
            token=refresh_token,
            token_type="refresh",
            device_id=device["device_id"],
            ttl_seconds=30 * 24 * 60 * 60,
        )
        store.set_pairing_status(pairing["pairing_id"], "completed")
        store.append_audit_event(
            event_type="device_registered",
            actor_type="device",
            actor_id=device["device_id"],
            node_id=pairing["node_id"],
            request_id=_request_id(request),
            payload_redacted={
                "pairing_id": pairing["pairing_id"],
                "platform": payload.device.platform,
                "permissions": permissions,
            },
        )
        store.create_event(
            node_id=pairing["node_id"],
            event_type="system.health",
            payload={"status": "healthy", "reason": "device_registered"},
        )
        return CompletePairingResponse(
            node=Node.model_validate(store.get_node(pairing["node_id"])),
            device=Device.model_validate(device),
            tokens=AuthTokenSet(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=now_utc() + timedelta(minutes=15),
            ),
        )

    @app.post("/v1/auth/token/refresh", response_model=AuthTokenSet)
    def refresh_token(
        payload: RefreshTokenRequest,
        signed_device: VerifiedDevice = signed_device_dependency,
    ) -> AuthTokenSet:
        device = store.verify_refresh_token(payload.refresh_token)
        if device is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")
        if device["device_id"] != signed_device.device_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "refresh token device mismatch")
        access_token = new_token()
        refresh_token_value = new_token()
        store.create_auth_token(
            token=access_token,
            token_type="access",
            device_id=device["device_id"],
            ttl_seconds=15 * 60,
        )
        store.create_auth_token(
            token=refresh_token_value,
            token_type="refresh",
            device_id=device["device_id"],
            ttl_seconds=30 * 24 * 60 * 60,
        )
        return AuthTokenSet(
            access_token=access_token,
            refresh_token=refresh_token_value,
            expires_at=expires_in(15 * 60),
        )

    @app.get("/v1/devices")
    def list_devices(
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[Device]]:
        return {"devices": [Device.model_validate(device) for device in store.list_devices()]}

    @app.delete("/v1/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
    def revoke_device(
        device_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> None:
        if not store.revoke_device(device_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
        store.append_audit_event(
            event_type="device_revoked",
            actor_type="device",
            actor_id=device.device_id,
            node_id=resolved_settings.node_id,
            request_id=_request_id(request),
            payload_redacted={"device_id": device_id},
        )

    @app.post("/v1/approvals", response_model=ApprovalRequest, status_code=status.HTTP_201_CREATED)
    def create_approval(
        payload: CreateApprovalRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalRequest:
        return _create_approval_request(
            store=store,
            settings=resolved_settings,
            request=request,
            payload=payload,
        )

    @app.post(
        "/v1/hermes/tools/approval_requested",
        response_model=ApprovalRequest,
        status_code=status.HTTP_201_CREATED,
    )
    def hermes_approval_requested(
        payload: HermesApprovalRequestedRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalRequest:
        approval_payload = CreateApprovalRequest(
            action_id=payload.action_id or new_id("act"),
            node_id=payload.node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            requested_tool=payload.requested_tool,
            risk_level=payload.risk_level,
            risk_category=payload.risk_category,
            summary=payload.summary,
            full_payload_redacted=payload.payload_redacted,
            resource_scope=payload.resource_scope,
            options=_approval_options_from_scopes(payload.suggested_scopes),
            expires_at=expires_in(payload.expires_in_seconds),
        )
        return _create_approval_request(
            store=store,
            settings=resolved_settings,
            request=request,
            payload=approval_payload,
        )

    @app.post("/v1/hermes/tools/approval_status", response_model=ApprovalStatusResponse)
    def hermes_approval_status(
        payload: ApprovalStatusRequest,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> ApprovalStatusResponse:
        _expire_pending_approvals(store)
        try:
            approval = store.get_approval(payload.approval_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
        return ApprovalStatusResponse(
            approval_id=approval["approval_id"],
            state=approval["state"],
            selected_scope=approval["decision_scope"] if approval["state"] == "approved" else None,
            decided_at=approval["decided_at"],
            decision_metadata=approval["decision_metadata"],
        )

    @app.get("/v1/approvals")
    def list_approvals(
        state: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[ApprovalRequest]]:
        _expire_pending_approvals(store)
        return {
            "approvals": [
                ApprovalRequest.model_validate(approval)
                for approval in store.list_approvals(state=state)
            ]
        }

    @app.get("/v1/approvals/{approval_id}", response_model=ApprovalRequest)
    def get_approval(
        approval_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalRequest:
        _expire_pending_approvals(store)
        try:
            return ApprovalRequest.model_validate(store.get_approval(approval_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc

    @app.post("/v1/approvals/{approval_id}/decisions", response_model=ApprovalDecisionResponse)
    def decide_approval(
        approval_id: str,
        payload: ApprovalDecisionRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalDecisionResponse:
        _require_approval_capability(
            store=store,
            settings=resolved_settings,
            request=request,
            device=device,
            approval_id=approval_id,
        )
        state = "approved" if payload.decision == "approve" else "denied"
        return _transition_approval(
            store=store,
            approval_id=approval_id,
            target_state=state,
            request_id=_request_id(request),
            actor_device_id=device.device_id,
            decision=payload.decision,
            scope=payload.scope,
        )

    @app.post("/v1/approvals/{approval_id}/approve_once", response_model=ApprovalDecisionResponse)
    def approve_once(
        approval_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalDecisionResponse:
        _require_approval_capability(
            store=store,
            settings=resolved_settings,
            request=request,
            device=device,
            approval_id=approval_id,
        )
        return _transition_approval(
            store=store,
            approval_id=approval_id,
            target_state="approved",
            request_id=_request_id(request),
            actor_device_id=device.device_id,
            decision="approve",
            scope="once",
        )

    @app.post("/v1/approvals/{approval_id}/deny", response_model=ApprovalDecisionResponse)
    def deny_approval(
        approval_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalDecisionResponse:
        _require_approval_capability(
            store=store,
            settings=resolved_settings,
            request=request,
            device=device,
            approval_id=approval_id,
        )
        return _transition_approval(
            store=store,
            approval_id=approval_id,
            target_state="denied",
            request_id=_request_id(request),
            actor_device_id=device.device_id,
            decision="deny",
            scope="once",
        )

    @app.post("/v1/approvals/{approval_id}/expire", response_model=ApprovalDecisionResponse)
    def expire_approval(
        approval_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalDecisionResponse:
        _require_approval_capability(
            store=store,
            settings=resolved_settings,
            request=request,
            device=device,
            approval_id=approval_id,
        )
        return _transition_approval(
            store=store,
            approval_id=approval_id,
            target_state="expired",
            request_id=_request_id(request),
            actor_device_id=device.device_id,
            decision=None,
            scope=None,
        )

    @app.post("/v1/approvals/{approval_id}/cancel", response_model=ApprovalDecisionResponse)
    def cancel_approval(
        approval_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalDecisionResponse:
        _require_approval_capability(
            store=store,
            settings=resolved_settings,
            request=request,
            device=device,
            approval_id=approval_id,
        )
        return _transition_approval(
            store=store,
            approval_id=approval_id,
            target_state="cancelled",
            request_id=_request_id(request),
            actor_device_id=device.device_id,
            decision=None,
            scope=None,
        )

    @app.post(
        "/v1/notifications/mobile_notify",
        response_model=Notification,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def mobile_notify(
        payload: MobileNotifyRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> Notification:
        return _create_mobile_notification(
            store=store,
            settings=resolved_settings,
            request=request,
            payload=payload,
        )

    @app.post(
        "/v1/hermes/tools/mobile_notify",
        response_model=Notification,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def hermes_mobile_notify(
        payload: MobileNotifyRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> Notification:
        return _create_mobile_notification(
            store=store,
            settings=resolved_settings,
            request=request,
            payload=payload,
        )

    @app.get("/v1/notifications")
    def list_notifications(
        category: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[Notification]]:
        return {
            "notifications": [
                Notification.model_validate(notification)
                for notification in store.list_notifications(category=category)
            ]
        }

    @app.get("/v1/audit/events")
    def list_audit_events(
        event_type: str | None = None,
        limit: int = 100,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[dict[str, Any]]]:
        return {"audit_events": store.list_audit_events(event_type=event_type, limit=limit)}

    @app.get("/v1/operator-sessions")
    def list_operator_sessions(
        session_type: str | None = None,
        state: str | None = None,
        agent_id: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[OperatorSession]]:
        return {
            "operator_sessions": [
                OperatorSession.model_validate(session)
                for session in store.list_operator_sessions(
                    session_type=session_type,
                    state=state,
                    agent_id=agent_id,
                )
            ]
        }

    @app.post("/v1/sessions/{session_id}/interventions", response_model=InterventionResponse)
    def session_intervention(
        session_id: str,
        payload: InterventionRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> InterventionResponse:
        # Change 4 — panic dominance. Emergency interventions BULK-INVALIDATE
        # every pending AND approved-but-unconsumed (approved/reserved) clearance
        # for the session; committed clearances are already consumed and left
        # intact. Non-emergency interventions are recorded.
        emergency_types = {
            "emergency_stop",
            "kill_task",
            "kill_agent",
            "quarantine_agent",
            "cancel_task",
        }
        invalidated: list[str] = []
        if payload.type in emergency_types:
            invalidated = store.bulk_invalidate_approvals(
                session_id=session_id, reason=f"intervention:{payload.type}"
            )
            resulting_state = "approvals_invalidated"
        else:
            resulting_state = "recorded"
        store.append_audit_event(
            event_type="intervention_requested",
            actor_type="device",
            actor_id=device.device_id,
            node_id=resolved_settings.node_id,
            session_id=session_id,
            request_id=_request_id(request),
            payload_redacted={
                "type": payload.type,
                "reason": payload.reason,
                "invalidated_count": len(invalidated),
            },
        )
        return InterventionResponse(
            intervention_id=payload.intervention_id,
            resulting_state=resulting_state,
        )

    @app.post(
        "/v1/tui/sessions",
        response_model=TuiSession,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_tui_session(
        payload: CreateTuiSessionRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> TuiSession:
        node_id = payload.node_id or resolved_settings.node_id
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="tui",
            request_id=_request_id(request),
            node_id=node_id,
            agent_id=payload.agent_id,
        )
        await tui_manager.cleanup_idle_sessions()
        if store.count_open_tui_sessions() >= resolved_settings.tui_max_sessions:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "TUI session limit reached")

        command, working_directory = validate_tui_request(
            settings=resolved_settings,
            command=payload.command,
            working_directory=payload.working_directory,
        )
        session_id = new_id("tui")
        _require_tui_capability(store, node_id=node_id, agent_id=payload.agent_id)
        session = store.create_tui_session(
            {
                "session_id": session_id,
                "agent_id": payload.agent_id,
                "node_id": node_id,
                "user_device_id": device.device_id,
                "state": "requested",
                "command": command,
                "working_directory": working_directory,
                "risk_level": payload.risk_level,
                "risk_label": _tui_risk_label(payload.risk_level),
                "output_retention_enabled": resolved_settings.tui_output_retention_enabled,
            }
        )
        try:
            await tui_manager.create_runtime(
                session_id=session_id,
                command=command,
                working_directory=working_directory,
            )
            session = store.update_tui_session_state(session_id, "active")
        except HTTPException:
            store.update_tui_session_state(session_id, "failed")
            raise
        except Exception as exc:
            store.update_tui_session_state(session_id, "failed")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "TUI session failed to start",
            ) from exc

        audit = store.append_audit_event(
            event_type="tui_session_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=session_id,
            request_id=_request_id(request),
            payload_redacted={
                "command": command,
                "working_directory": working_directory,
                "risk_level": payload.risk_level,
                "hermes_session_id": payload.session_context_id,
            },
        )
        session = store.add_tui_audit_ref(session_id, audit["audit_event_id"])
        store.create_operator_session(
            {
                "session_id": session_id,
                "session_type": "tui",
                "agent_id": payload.agent_id,
                "state": session["state"],
                "owner_device_id": device.device_id,
                "capability_requirements": ["tui"],
                "context": {
                    "hermes_session_id": payload.session_context_id,
                    "command": command,
                    "working_directory": working_directory,
                    "risk_level": payload.risk_level,
                },
            }
        )
        store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=session_id,
            event_type="tui.session.state",
            payload={"session_id": session_id, "state": session["state"]},
        )
        return TuiSession.model_validate(session)

    @app.post(
        "/v1/tui/sessions/{session_id}/attach-token",
        response_model=TuiAttachTokenResponse,
    )
    def create_tui_attach_token(
        session_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> TuiAttachTokenResponse:
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="tui",
            request_id=_request_id(request),
        )
        session = _owned_tui_session(store, session_id, device)
        if session["state"] in {"closed", "failed"}:
            raise HTTPException(status.HTTP_409_CONFLICT, "TUI session is not attachable")
        token = new_token()
        attach = store.create_tui_attach_token(
            token=token,
            session_id=session_id,
            device_id=device.device_id,
            ttl_seconds=resolved_settings.tui_attach_token_ttl_seconds,
        )
        store.append_audit_event(
            event_type="tui_attach_token_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session_id,
            request_id=_request_id(request),
            payload_redacted={"expires_at": attach["expires_at"]},
        )
        return TuiAttachTokenResponse.model_validate(attach)

    @app.get("/v1/tui/sessions")
    async def list_tui_sessions(
        state: str | None = None,
        device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[TuiSession]]:
        await tui_manager.cleanup_idle_sessions()
        return {
            "sessions": [
                TuiSession.model_validate(session)
                for session in store.list_tui_sessions(
                    user_device_id=device.device_id,
                    state=state,
                )
            ]
        }

    @app.get("/v1/tui/sessions/{session_id}", response_model=TuiSession)
    async def get_tui_session(
        session_id: str,
        device: VerifiedDevice = signed_device_dependency,
    ) -> TuiSession:
        await tui_manager.cleanup_idle_sessions()
        session = _owned_tui_session(store, session_id, device)
        return TuiSession.model_validate(session)

    @app.post("/v1/tui/sessions/{session_id}/detach", response_model=TuiSessionControlResponse)
    async def detach_tui_session(
        session_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> TuiSessionControlResponse:
        session = _owned_tui_session(store, session_id, device)
        if session["state"] in {"closed", "failed"}:
            raise HTTPException(status.HTTP_409_CONFLICT, "TUI session is not attachable")
        await tui_manager.detach(session_id)
        session = _record_tui_state_change(
            store=store,
            session_id=session_id,
            event_type="tui_session_detached",
            request_id=_request_id(request),
            actor_device_id=device.device_id,
        )
        return TuiSessionControlResponse(session=TuiSession.model_validate(session))

    @app.post("/v1/tui/sessions/{session_id}/close", response_model=TuiSessionControlResponse)
    async def close_tui_session(
        session_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> TuiSessionControlResponse:
        session = _owned_tui_session(store, session_id, device)
        if session["state"] == "closed":
            return TuiSessionControlResponse(session=TuiSession.model_validate(session))
        await tui_manager.close(session_id)
        session = _record_tui_state_change(
            store=store,
            session_id=session_id,
            event_type="tui_session_closed",
            request_id=_request_id(request),
            actor_device_id=device.device_id,
        )
        return TuiSessionControlResponse(session=TuiSession.model_validate(session))

    @app.post(
        "/v1/tua/requests",
        response_model=AssistanceRequest,
        status_code=status.HTTP_201_CREATED,
    )
    def create_tua_request(
        payload: CreateAssistanceRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> AssistanceRequest:
        node_id = payload.node_id or resolved_settings.node_id
        assistance_request = store.create_assistance_request(
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
        store.append_audit_event(
            event_type="tua_request_created",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            request_id=_request_id(request),
            payload_redacted={"request_id": assistance_request["request_id"]},
        )
        store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="tua.requested",
            payload={"request_id": assistance_request["request_id"]},
        )
        return AssistanceRequest.model_validate(assistance_request)

    @app.get("/v1/tua/requests")
    def list_tua_requests(
        state: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[AssistanceRequest]]:
        return {
            "requests": [
                AssistanceRequest.model_validate(item)
                for item in store.list_assistance_requests(state=state)
            ]
        }

    @app.get("/v1/tua/requests/{request_id}", response_model=AssistanceRequest)
    def get_tua_request(
        request_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> AssistanceRequest:
        try:
            return AssistanceRequest.model_validate(store.get_assistance_request(request_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "TUA request not found") from exc

    @app.post(
        "/v1/tua/requests/{request_id}/sessions",
        response_model=AssistanceSession,
        status_code=status.HTTP_201_CREATED,
    )
    def create_tua_session(
        request_id: str,
        payload: CreateAssistanceSessionRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> AssistanceSession:
        try:
            assistance_request = store.get_assistance_request(request_id)
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "TUA request not found") from exc
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="tua",
            request_id=_request_id(request),
            node_id=assistance_request["node_id"],
            agent_id=assistance_request["agent_id"],
        )
        session = store.create_assistance_session(
            {
                "request_id": request_id,
                "node_id": assistance_request["node_id"],
                "agent_id": assistance_request["agent_id"],
                "session_id": assistance_request["session_id"],
                "state": "active",
                "created_by_device_id": device.device_id,
            }
        )
        if payload.initial_message:
            store.create_assistance_message(
                {
                    "assistance_session_id": session["assistance_session_id"],
                    "sender_type": "user",
                    "sender_id": device.device_id,
                    "body": payload.initial_message,
                }
            )
            session = store.get_assistance_session(session["assistance_session_id"])
        store.append_audit_event(
            event_type="tua_session_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={"assistance_session_id": session["assistance_session_id"]},
        )
        store.create_operator_session(
            {
                "session_id": session["assistance_session_id"],
                "session_type": "tua",
                "agent_id": session["agent_id"],
                "mission_id": _mission_id_from_context(
                    assistance_request.get("context_redacted", {})
                ),
                "state": session["state"],
                "owner_device_id": device.device_id,
                "capability_requirements": ["tua"],
                "context": assistance_request.get("context_redacted", {}),
            }
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="tua.session.created",
            payload={"assistance_session_id": session["assistance_session_id"]},
        )
        return AssistanceSession.model_validate(session)

    @app.get("/v1/tua/sessions/{session_id}", response_model=AssistanceSession)
    def get_tua_session(
        session_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> AssistanceSession:
        try:
            return AssistanceSession.model_validate(store.get_assistance_session(session_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "TUA session not found") from exc

    @app.post(
        "/v1/tua/sessions/{session_id}/messages",
        response_model=AssistanceMessage,
        status_code=status.HTTP_201_CREATED,
    )
    def create_tua_message(
        session_id: str,
        payload: CreateAssistanceMessageRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> AssistanceMessage:
        session = _get_assistance_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="tua",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        message = store.create_assistance_message(
            {
                "assistance_session_id": session_id,
                "sender_type": "user",
                "sender_id": device.device_id,
                "body": payload.body,
            }
        )
        store.append_audit_event(
            event_type="tua_message_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={
                "message_id": message["message_id"],
                "body_length": len(payload.body),
            },
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="tua.message.created",
            payload={"assistance_session_id": session_id, "message_id": message["message_id"]},
        )
        return AssistanceMessage.model_validate(message)

    @app.post("/v1/tua/sessions/{session_id}/return-control", response_model=AssistanceSession)
    def return_tua_control(
        session_id: str,
        payload: ReturnControlRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> AssistanceSession:
        session = _get_assistance_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="tua",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        updated = store.update_assistance_session_state(
            session_id,
            "returned_to_agent",
            return_summary=payload.summary,
        )
        store.append_audit_event(
            event_type="tua_returned_to_agent",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={"summary_length": len(payload.summary)},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="tua.returned_to_agent",
            payload={"assistance_session_id": session_id},
        )
        _update_operator_session_if_exists(
            store,
            session_id,
            "returned_to_agent",
            owner_device_id=device.device_id,
            return_summary=payload.summary,
        )
        return AssistanceSession.model_validate(updated)

    @app.post("/v1/tua/sessions/{session_id}/close", response_model=AssistanceSession)
    def close_tua_session(
        session_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> AssistanceSession:
        session = _get_assistance_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="tua",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        updated = store.update_assistance_session_state(session_id, "closed")
        store.append_audit_event(
            event_type="tua_session_closed",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="tua.closed",
            payload={"assistance_session_id": session_id},
        )
        _update_operator_session_if_exists(
            store,
            session_id,
            "closed",
            owner_device_id=device.device_id,
        )
        return AssistanceSession.model_validate(updated)

    @app.post(
        "/v1/browser-assistance/sessions",
        response_model=BrowserAssistanceSession,
        status_code=status.HTTP_201_CREATED,
    )
    def create_browser_assistance_session(
        payload: CreateBrowserAssistanceSessionRequest,
        request: Request,
        _caller: HermesLocalCaller = hermes_local_dependency,
    ) -> BrowserAssistanceSession:
        node_id = payload.node_id or resolved_settings.node_id
        session = store.create_browser_assistance_session(
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
        store.append_audit_event(
            event_type="browser_assistance_requested",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            request_id=_request_id(request),
            payload_redacted={"browser_session_id": session["browser_session_id"]},
        )
        store.create_operator_session(
            {
                "session_id": session["browser_session_id"],
                "session_type": "browser_assistance",
                "agent_id": session["agent_id"],
                "mission_id": _mission_id_from_context(payload.context_redacted),
                "state": session["state"],
                "capability_requirements": ["browser_assistance"],
                "context": payload.context_redacted,
            }
        )
        store.create_event(
            node_id=node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            event_type="browser_assistance.requested",
            payload={"browser_session_id": session["browser_session_id"]},
        )
        return BrowserAssistanceSession.model_validate(session)

    @app.get("/v1/browser-assistance/sessions")
    def list_browser_assistance_sessions(
        state: str | None = None,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[BrowserAssistanceSession]]:
        return {
            "sessions": [
                BrowserAssistanceSession.model_validate(item)
                for item in store.list_browser_assistance_sessions(state=state)
            ]
        }

    @app.get(
        "/v1/browser-assistance/sessions/{session_id}",
        response_model=BrowserAssistanceSession,
    )
    def get_browser_assistance_session(
        session_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> BrowserAssistanceSession:
        try:
            return BrowserAssistanceSession.model_validate(
                store.get_browser_assistance_session(session_id)
            )
        except KeyError as exc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "browser assistance session not found"
            ) from exc

    @app.post(
        "/v1/browser-assistance/sessions/{session_id}/event",
        response_model=BrowserAssistanceSession,
    )
    def add_browser_assistance_event(
        session_id: str,
        payload: BrowserAssistanceEventRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> BrowserAssistanceSession:
        session = _get_browser_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="browser_assistance",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        updated = store.add_browser_assistance_note(session_id, payload.note)
        store.append_audit_event(
            event_type="browser_assistance_event_recorded",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={"note_length": len(payload.note)},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="browser_assistance.event",
            payload={"browser_session_id": session_id},
        )
        _update_operator_session_if_exists(
            store,
            session_id,
            "user_controlling",
            owner_device_id=device.device_id,
        )
        return BrowserAssistanceSession.model_validate(updated)

    @app.post(
        "/v1/browser-assistance/sessions/{session_id}/return-control",
        response_model=BrowserAssistanceSession,
    )
    def return_browser_assistance_control(
        session_id: str,
        payload: ReturnControlRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> BrowserAssistanceSession:
        session = _get_browser_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="browser_assistance",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        updated = store.update_browser_assistance_state(
            session_id,
            "returned_to_agent",
            return_summary=payload.summary,
        )
        store.append_audit_event(
            event_type="browser_assistance_returned_to_agent",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={"summary_length": len(payload.summary)},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="browser_assistance.returned_to_agent",
            payload={"browser_session_id": session_id},
        )
        _update_operator_session_if_exists(
            store,
            session_id,
            "returned_to_agent",
            owner_device_id=device.device_id,
            return_summary=payload.summary,
        )
        return BrowserAssistanceSession.model_validate(updated)

    @app.post(
        "/v1/browser-assistance/sessions/{session_id}/close",
        response_model=BrowserAssistanceSession,
    )
    def close_browser_assistance_session(
        session_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> BrowserAssistanceSession:
        session = _get_browser_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="browser_assistance",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        updated = store.update_browser_assistance_state(session_id, "closed")
        store.append_audit_event(
            event_type="browser_assistance_closed",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            request_id=_request_id(request),
            payload_redacted={},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session["session_id"],
            event_type="browser_assistance.closed",
            payload={"browser_session_id": session_id},
        )
        _update_operator_session_if_exists(
            store,
            session_id,
            "closed",
            owner_device_id=device.device_id,
        )
        return BrowserAssistanceSession.model_validate(updated)

    @app.post(
        "/v1/approvals/{approval_id}/responses",
        response_model=ApprovalResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_approval_response(
        approval_id: str,
        payload: CreateApprovalResponseRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> ApprovalResponse:
        approval = _get_approval_or_404(store, approval_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="approvals",
            request_id=_request_id(request),
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
        )
        policy_proposal_id = None
        if payload.decision_type == "propose_policy":
            if payload.confirmation_phrase != "PROPOSE POLICY":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "policy proposal requires explicit confirmation phrase",
                )
            proposal = store.create_approval_policy_proposal(
                {
                    "approval_id": approval_id,
                    "created_by_device_id": device.device_id,
                    "status": "proposed",
                    "warning": "Proposal only; no permanent allow policy was activated.",
                    "constraints": [item.model_dump() for item in payload.constraints],
                }
            )
            policy_proposal_id = proposal["policy_proposal_id"]
        response = store.create_approval_response(
            {
                "approval_id": approval_id,
                "decision_type": payload.decision_type,
                "created_by_device_id": device.device_id,
                "user_message": payload.user_message,
                "alternate_directive": payload.alternate_directive,
                "constraints": [item.model_dump() for item in payload.constraints],
                "policy_proposal_id": policy_proposal_id,
            }
        )
        if payload.decision_type in {"approve_once", "approve_session", "approve_agent", "deny"}:
            transition = {
                "approve_once": ("approved", "approve", "once"),
                "approve_session": ("approved", "approve", "session"),
                "approve_agent": ("approved", "approve", "agent"),
                "deny": ("denied", "deny", "once"),
            }[payload.decision_type]
            _transition_approval(
                store=store,
                approval_id=approval_id,
                target_state=transition[0],
                request_id=_request_id(request),
                actor_device_id=device.device_id,
                decision=transition[1],
                scope=transition[2],
            )
        store.append_audit_event(
            event_type="approval_response_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            approval_id=approval_id,
            request_id=_request_id(request),
            payload_redacted={
                "decision_type": payload.decision_type,
                "constraint_count": len(payload.constraints),
                "policy_proposal_id": policy_proposal_id,
            },
        )
        event_type = (
            "approval.needs_info"
            if payload.decision_type == "needs_info"
            else "approval.response.created"
        )
        store.create_event(
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            event_type=event_type,
            payload={
                "approval_id": approval_id,
                "approval_response_id": response["approval_response_id"],
                "decision_type": payload.decision_type,
            },
        )
        return ApprovalResponse.model_validate(response)

    @app.get(
        "/v1/approvals/{approval_id}/policy-proposals",
    )
    def list_approval_policy_proposals(
        approval_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, list[ApprovalPolicyProposal]]:
        _get_approval_or_404(store, approval_id)
        responses = store.list_approval_responses(approval_id)
        proposals = []
        for response in responses:
            proposal_id = response.get("policy_proposal_id")
            if proposal_id:
                proposals.append(
                    ApprovalPolicyProposal.model_validate(
                        store.get_approval_policy_proposal(proposal_id)
                    )
                )
        return {"policy_proposals": proposals}

    @app.post(
        "/v1/voice/sessions",
        response_model=VoiceSession,
        status_code=status.HTTP_201_CREATED,
    )
    def create_voice_session(
        payload: CreateVoiceSessionRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> VoiceSession:
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="voice",
            request_id=_request_id(request),
            agent_id=payload.agent_id,
        )
        session = store.create_voice_session(
            {
                "node_id": resolved_settings.node_id,
                "agent_id": payload.agent_id,
                "session_id": payload.session_id,
                "created_by_device_id": device.device_id,
                "mode": payload.mode,
                "state": "active",
            }
        )
        store.append_audit_event(
            event_type="voice_session_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session.get("session_id"),
            voice_session_id=session["voice_session_id"],
            request_id=_request_id(request),
            payload_redacted={"mode": payload.mode},
        )
        store.create_operator_session(
            {
                "session_id": session["voice_session_id"],
                "session_type": "voice",
                "agent_id": session["agent_id"],
                "state": session["state"],
                "owner_device_id": device.device_id,
                "capability_requirements": ["voice"],
                "context": {"hermes_session_id": payload.session_id, "mode": payload.mode},
            }
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session.get("session_id"),
            event_type="voice.session.created",
            payload={"voice_session_id": session["voice_session_id"], "mode": payload.mode},
        )
        return VoiceSession.model_validate(session)

    @app.get("/v1/voice/sessions/{session_id}", response_model=VoiceSession)
    def get_voice_session(
        session_id: str,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> VoiceSession:
        try:
            return VoiceSession.model_validate(store.get_voice_session(session_id))
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "voice session not found") from exc

    @app.post(
        "/v1/voice/sessions/{session_id}/messages",
        response_model=VoiceMessage,
        status_code=status.HTTP_201_CREATED,
    )
    def create_voice_message(
        session_id: str,
        payload: CreateVoiceMessageRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> VoiceMessage:
        session = _get_voice_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="voice",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        message = store.create_voice_message(
            {
                "voice_session_id": session_id,
                "sender_type": "user",
                "body": payload.body,
                "input_mode": payload.input_mode,
            }
        )
        store.append_audit_event(
            event_type="voice_message_created",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session.get("session_id"),
            voice_session_id=session_id,
            request_id=_request_id(request),
            payload_redacted={"input_mode": payload.input_mode, "body_length": len(payload.body)},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session.get("session_id"),
            event_type="voice.message.created",
            payload={
                "voice_session_id": session_id,
                "voice_message_id": message["voice_message_id"],
            },
        )
        return VoiceMessage.model_validate(message)

    @app.post("/v1/voice/sessions/{session_id}/close", response_model=VoiceSession)
    def close_voice_session(
        session_id: str,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> VoiceSession:
        session = _get_voice_session_or_404(store, session_id)
        require_device_capability(
            store=store,
            settings=resolved_settings,
            device=device,
            capability="voice",
            request_id=_request_id(request),
            node_id=session["node_id"],
            agent_id=session["agent_id"],
        )
        updated = store.update_voice_session_state(session_id, "closed")
        store.append_audit_event(
            event_type="voice_session_closed",
            actor_type="device",
            actor_id=device.device_id,
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session.get("session_id"),
            voice_session_id=session_id,
            request_id=_request_id(request),
            payload_redacted={},
        )
        store.create_event(
            node_id=session["node_id"],
            agent_id=session["agent_id"],
            session_id=session.get("session_id"),
            event_type="voice.session.closed",
            payload={"voice_session_id": session_id},
        )
        _update_operator_session_if_exists(
            store,
            session_id,
            "closed",
            owner_device_id=device.device_id,
        )
        return VoiceSession.model_validate(updated)

    @app.get("/v1/events")
    def list_events(
        after: str | None = None,
        limit: int = 500,
        _device: VerifiedDevice = signed_device_dependency,
    ) -> dict[str, Any]:
        events = store.list_events_after(after=after, limit=limit)
        return {"events": events, "next_cursor": events[-1]["cursor"] if events else after}

    @app.websocket("/v1/events/stream")
    async def event_stream(websocket: WebSocket) -> None:
        token = _websocket_token(websocket)
        if not token or store.verify_access_token(token) is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        after = websocket.query_params.get("after")
        heartbeat = store.create_event(
            node_id=resolved_settings.node_id,
            event_type="system.health",
            payload={"status": "healthy", "reason": "websocket_connected"},
        )
        await websocket.accept()
        events = store.list_events_after(after=after)
        if not events:
            events = [heartbeat]
        try:
            for event in events:
                await websocket.send_json(event)
            while True:
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                except TimeoutError:
                    event = store.create_event(
                        node_id=resolved_settings.node_id,
                        event_type="system.health",
                        payload={"status": "healthy", "reason": "heartbeat"},
                    )
                    await websocket.send_json(event)
                    continue
                if message == "ping":
                    await websocket.send_json(
                        store.create_event(
                            node_id=resolved_settings.node_id,
                            event_type="system.health",
                            payload={"status": "healthy", "reason": "pong"},
                        )
                    )
        except WebSocketDisconnect:
            return

    @app.websocket("/v1/tui/sessions/{session_id}/stream")
    async def tui_stream(websocket: WebSocket, session_id: str) -> None:
        attach_token = websocket.query_params.get("attach_token")
        attach = store.verify_tui_attach_token(attach_token) if attach_token else None
        if attach is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        try:
            session = store.get_tui_session(session_id)
        except KeyError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        if (
            attach["session_id"] != session_id
            or session["user_device_id"] != attach["device_id"]
        ):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        if session["state"] in {"closed", "failed"} or not tui_manager.is_running(session_id):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await tui_manager.attach(session_id)
        await websocket.accept()
        await websocket.send_json(
            {"type": "state", "session_id": session_id, "state": "active"}
        )
        await websocket.send_json(
            {
                "type": "audit_notice",
                "session_id": session_id,
                "message": "TUI I/O metadata is audited; terminal contents are not logged.",
            }
        )
        receive_task = asyncio.create_task(websocket.receive_json())
        try:
            while True:
                output = await tui_manager.next_output(session_id, timeout=0.05)
                if output:
                    await websocket.send_json(
                        {"type": "output", "session_id": session_id, "data": output}
                    )

                if not receive_task.done():
                    await asyncio.sleep(0.01)
                    continue

                frame = validate_tui_frame(receive_task.result())
                if await _handle_tui_frame(
                    frame=frame,
                    session_id=session_id,
                    websocket=websocket,
                    store=store,
                    tui_manager=tui_manager,
                    device_id=attach["device_id"],
                ):
                    return
                receive_task = asyncio.create_task(websocket.receive_json())
        except WebSocketDisconnect:
            await tui_manager.detach(session_id)
        except ValueError as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})
        finally:
            if not receive_task.done():
                receive_task.cancel()

    return app


def _ensure_local_node(store: SQLiteStore, settings: Settings) -> None:
    store.upsert_node(
        {
            "node_id": settings.node_id,
            "display_name": settings.node_display_name,
            "environment": settings.node_environment,
            "gateway_base_url": settings.gateway_base_url,
            "node_fingerprint": settings.node_fingerprint,
            "gateway_version": settings.gateway_version,
            "hermes_version": settings.hermes_version,
            "health": "online",
            "tags": ["self-hosted", "tailscale-first"],
        }
    )


def _create_approval_request(
    *,
    store: SQLiteStore,
    settings: Settings,
    request: Request,
    payload: CreateApprovalRequest,
) -> ApprovalRequest:
    node_id = payload.node_id or settings.node_id
    approval_id = new_id("appr")
    approval = store.create_approval(
        {
            "approval_id": approval_id,
            "action_id": payload.action_id,
            "node_id": node_id,
            "agent_id": payload.agent_id,
            "session_id": payload.session_id,
            "requested_tool": payload.requested_tool,
            "risk_level": payload.risk_level,
            "risk_category": payload.risk_category or "unknown_action",
            "risk_vector": payload.risk_vector.model_dump()
            if payload.risk_vector
            else None,
            "summary": payload.summary,
            "full_payload_redacted": payload.full_payload_redacted,
            "resource_scope": payload.resource_scope,
            "state": "pending",
            "options": payload.options or ["deny"],
            "expires_at": payload.expires_at.isoformat(),
        }
    )
    store.append_audit_event(
        event_type="approval_requested",
        actor_type="hermes",
        actor_id=payload.agent_id,
        node_id=node_id,
        agent_id=payload.agent_id,
        session_id=payload.session_id,
        approval_id=approval_id,
        request_id=_request_id(request),
        payload_redacted={
            "requested_tool": payload.requested_tool,
            "risk_level": payload.risk_level,
            "risk_category": payload.risk_category or "unknown_action",
        },
    )
    store.create_event(
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


def _create_mobile_notification(
    *,
    store: SQLiteStore,
    settings: Settings,
    request: Request,
    payload: MobileNotifyRequest,
) -> Notification:
    rejection_reason = _notification_rejection_reason(payload)
    if rejection_reason:
        store.append_audit_event(
            event_type="notification_rejected",
            actor_type="hermes",
            actor_id=payload.agent_id,
            node_id=settings.node_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            request_id=_request_id(request),
            payload_redacted={"category": payload.category, "reason": rejection_reason},
        )
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "notification body is not safe",
        )
    notification = store.create_notification(
        {
            "node_id": settings.node_id,
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
    store.append_audit_event(
        event_type="notification_queued",
        actor_type="hermes",
        actor_id=payload.agent_id,
        node_id=settings.node_id,
        agent_id=payload.agent_id,
        session_id=payload.session_id,
        notification_id=notification["notification_id"],
        request_id=_request_id(request),
        payload_redacted={"category": payload.category, "urgency": payload.urgency},
    )
    store.create_event(
        node_id=settings.node_id,
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


def _expire_pairing_if_needed(store: SQLiteStore, pairing: dict[str, Any]) -> dict[str, Any]:
    if pairing["status"] == "pending" and parse_utc(pairing["expires_at"]) <= now_utc():
        store.set_pairing_status(pairing["pairing_id"], "expired")
        pairing = store.get_pairing_session(
            pairing["pairing_id"], include_token="pairing_token_hash" in pairing
        )
    return pairing


def _expire_pending_approvals(store: SQLiteStore) -> None:
    for approval in store.list_approvals(state="pending"):
        if parse_utc(approval["expires_at"]) <= now_utc():
            store.resolve_approval(
                approval["approval_id"],
                "expired",
                decision_metadata={"reason": "expiry_scan"},
            )
            request_id = new_id("req")
            store.append_audit_event(
                event_type="approval_expired",
                actor_type="gateway",
                actor_id="gateway",
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                approval_id=approval["approval_id"],
                request_id=request_id,
                payload_redacted={"reason": "expiry_scan"},
            )
            store.create_event(
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                event_type="approval.resolved",
                payload={"approval_id": approval["approval_id"], "state": "expired"},
            )


def _transition_approval(
    *,
    store: SQLiteStore,
    approval_id: str,
    target_state: str,
    request_id: str,
    actor_device_id: str,
    decision: str | None,
    scope: str | None,
) -> ApprovalDecisionResponse:
    try:
        approval = store.get_approval(approval_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc

    if approval["state"] != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "approval is not pending")

    if target_state in {"approved", "denied"} and parse_utc(approval["expires_at"]) <= now_utc():
        store.resolve_approval(
            approval_id,
            "expired",
            decision_metadata={"reason": "decision_after_expiry"},
        )
        store.append_audit_event(
            event_type="approval_expired",
            actor_type="gateway",
            actor_id="gateway",
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            approval_id=approval_id,
            request_id=request_id,
            payload_redacted={"reason": "decision_after_expiry"},
        )
        store.create_event(
            node_id=approval["node_id"],
            agent_id=approval["agent_id"],
            session_id=approval["session_id"],
            event_type="approval.resolved",
            payload={"approval_id": approval_id, "state": "expired"},
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "approval expired")

    device_channel: str | None = None
    try:
        device_channel = channel_for_device(store.get_device(actor_device_id))
    except KeyError:
        device_channel = None

    # Change 5 — channel policy / risk tiering: a high-risk per-surface class can
    # mandate the mobile-signed channel. Fail-closed if the deciding channel does
    # not satisfy it. No risk_vector ⇒ no requirement ⇒ unchanged behavior.
    if target_state == "approved":
        required_channels = required_channels_for_risk_vector(
            approval.get("risk_vector")
        )
        if not channel_satisfies(device_channel, required_channels):
            store.append_audit_event(
                event_type="approval_channel_rejected",
                actor_type="device",
                actor_id=actor_device_id,
                node_id=approval["node_id"],
                agent_id=approval["agent_id"],
                session_id=approval["session_id"],
                approval_id=approval_id,
                request_id=request_id,
                payload_redacted={"required_channels": list(required_channels or ())},
            )
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "approval risk class requires a different decision channel",
            )

    # Change 1 — authority provenance.
    approved_by = authority_from_channel(device_channel)
    human_approved = target_state == "approved" and approved_by in {
        "human_mobile",
        "human_local",
    }
    store.resolve_approval(
        approval_id,
        target_state,
        decision_scope=scope,
        decision_actor_device_id=actor_device_id,
        decision_metadata={"decision": decision, "state": target_state},
        approved_by=approved_by,
        human_approved=human_approved,
    )
    event_type = {
        "approved": "approval_decision",
        "denied": "approval_decision",
        "expired": "approval_expired",
        "cancelled": "approval_cancelled",
    }[target_state]
    store.append_audit_event(
        event_type=event_type,
        actor_type="device",
        actor_id=actor_device_id,
        node_id=approval["node_id"],
        agent_id=approval["agent_id"],
        session_id=approval["session_id"],
        approval_id=approval_id,
        request_id=request_id,
        payload_redacted={
            "decision": decision,
            "scope": scope,
            "state": target_state,
        },
    )
    store.create_event(
        node_id=approval["node_id"],
        agent_id=approval["agent_id"],
        session_id=approval["session_id"],
        event_type="approval.resolved",
        payload={"approval_id": approval_id, "state": target_state, "scope": scope},
    )
    return ApprovalDecisionResponse(
        approval_id=approval_id,
        state=target_state,  # type: ignore[arg-type]
        applied_scope=scope,  # type: ignore[arg-type]
    )


def _require_permission(device: VerifiedDevice, permission: str) -> None:
    if permission not in device.permissions:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"device lacks {permission} permission")


def _require_tui_capability(store: SQLiteStore, *, node_id: str, agent_id: str) -> None:
    try:
        node = store.get_node(node_id)
        agent = store.get_agent(node_id, agent_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "TUI capability unavailable") from exc
    if _has_available_capability(node, "tui") or _has_available_capability(agent, "tui"):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "TUI capability unavailable")


def _has_available_capability(record: dict[str, Any], capability: str) -> bool:
    for item in record.get("capabilities", []):
        if item.get("name") == capability and item.get("status") == "available":
            return True
    return False


def _tui_risk_label(risk_level: str) -> str:
    return {
        "low": "operator terminal - low risk",
        "medium": "operator terminal - medium risk",
        "high": "operator terminal - high risk",
        "critical": "operator terminal - critical risk",
    }.get(risk_level, "operator terminal - high risk")


def _owned_tui_session(
    store: SQLiteStore,
    session_id: str,
    device: VerifiedDevice,
) -> dict[str, Any]:
    try:
        session = store.get_tui_session(session_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "TUI session not found") from exc
    if session["user_device_id"] != device.device_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "TUI session belongs to another device")
    return session


def _require_approval_capability(
    *,
    store: SQLiteStore,
    settings: Settings,
    request: Request,
    device: VerifiedDevice,
    approval_id: str,
) -> None:
    approval = _get_approval_or_404(store, approval_id)
    require_device_capability(
        store=store,
        settings=settings,
        device=device,
        capability="approvals",
        request_id=_request_id(request),
        node_id=approval["node_id"],
        agent_id=approval["agent_id"],
    )


def _mission_id_from_context(context: dict[str, Any]) -> str | None:
    value = context.get("mission_id")
    return value if isinstance(value, str) and value else None


def _update_operator_session_if_exists(
    store: SQLiteStore,
    session_id: str,
    state: str,
    *,
    owner_device_id: str | None = None,
    return_summary: str | None = None,
) -> None:
    try:
        store.update_operator_session_state(
            session_id,
            state,
            owner_device_id=owner_device_id,
            return_summary=return_summary,
        )
    except KeyError:
        return


def _get_approval_or_404(store: SQLiteStore, approval_id: str) -> dict[str, Any]:
    try:
        return store.get_approval(approval_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc


def _get_assistance_session_or_404(store: SQLiteStore, session_id: str) -> dict[str, Any]:
    try:
        return store.get_assistance_session(session_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "TUA session not found") from exc


def _get_browser_session_or_404(store: SQLiteStore, session_id: str) -> dict[str, Any]:
    try:
        return store.get_browser_assistance_session(session_id)
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "browser assistance session not found"
        ) from exc


def _get_voice_session_or_404(store: SQLiteStore, session_id: str) -> dict[str, Any]:
    try:
        return store.get_voice_session(session_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "voice session not found") from exc


def _record_tui_state_change(
    *,
    store: SQLiteStore,
    session_id: str,
    event_type: str,
    request_id: str,
    actor_device_id: str,
) -> dict[str, Any]:
    target_state = "closed" if event_type == "tui_session_closed" else "detached"
    session = store.update_tui_session_state(session_id, target_state)
    _update_operator_session_if_exists(
        store,
        session_id,
        session["state"],
        owner_device_id=actor_device_id,
    )
    audit = store.append_audit_event(
        event_type=event_type,
        actor_type="device",
        actor_id=actor_device_id,
        node_id=session["node_id"],
        agent_id=session["agent_id"],
        session_id=session_id,
        request_id=request_id,
        payload_redacted={"state": session["state"]},
    )
    session = store.add_tui_audit_ref(session_id, audit["audit_event_id"])
    store.create_event(
        node_id=session["node_id"],
        agent_id=session["agent_id"],
        session_id=session_id,
        event_type="tui.session.state",
        payload={"session_id": session_id, "state": session["state"]},
    )
    return session


async def _handle_tui_frame(
    *,
    frame: dict[str, Any],
    session_id: str,
    websocket: WebSocket,
    store: SQLiteStore,
    tui_manager: LocalPtyManager,
    device_id: str,
) -> bool:
    frame_type = frame["type"]
    if frame_type == "ping":
        await websocket.send_json({"type": "pong", "session_id": session_id})
        return False
    if frame_type == "resize":
        await tui_manager.resize(
            session_id,
            rows=int(frame.get("rows", 24)),
            cols=int(frame.get("cols", 80)),
        )
        return False
    if frame_type == "input":
        text = str(frame.get("data", ""))
        await tui_manager.write(session_id, text)
        _audit_tui_io_metadata(
            store=store,
            session_id=session_id,
            device_id=device_id,
            event_type="tui_input_sent",
            byte_count=len(text.encode("utf-8")),
            line_count=max(text.count("\n"), 1 if text else 0),
        )
        return False
    if frame_type == "paste":
        text = str(frame.get("data", frame.get("text", "")))
        await tui_manager.write(session_id, text)
        _audit_tui_io_metadata(
            store=store,
            session_id=session_id,
            device_id=device_id,
            event_type="tui_paste_sent",
            byte_count=len(text.encode("utf-8")),
            line_count=max(text.count("\n"), 1 if text else 0),
            risk_warnings=_paste_risk_warnings(text),
        )
        return False
    if frame_type == "detach":
        await tui_manager.detach(session_id)
        _record_tui_state_change(
            store=store,
            session_id=session_id,
            event_type="tui_session_detached",
            request_id=new_id("req"),
            actor_device_id=device_id,
        )
        await websocket.send_json(
            {"type": "state", "session_id": session_id, "state": "detached"}
        )
        await websocket.close()
        return True
    if frame_type == "close":
        await tui_manager.close(session_id)
        _record_tui_state_change(
            store=store,
            session_id=session_id,
            event_type="tui_session_closed",
            request_id=new_id("req"),
            actor_device_id=device_id,
        )
        await websocket.send_json({"type": "state", "session_id": session_id, "state": "closed"})
        await websocket.close()
        return True
    return False


def _audit_tui_io_metadata(
    *,
    store: SQLiteStore,
    session_id: str,
    device_id: str,
    event_type: str,
    byte_count: int,
    line_count: int,
    risk_warnings: list[str] | None = None,
) -> None:
    session = store.get_tui_session(session_id)
    audit = store.append_audit_event(
        event_type=event_type,
        actor_type="device",
        actor_id=device_id,
        node_id=session["node_id"],
        agent_id=session["agent_id"],
        session_id=session_id,
        request_id=new_id("req"),
        payload_redacted={
            "byte_count": byte_count,
            "line_count": line_count,
            "risk_warnings": risk_warnings or [],
            "contents_logged": False,
        },
    )
    store.add_tui_audit_ref(session_id, audit["audit_event_id"])


def _paste_risk_warnings(text: str) -> list[str]:
    warnings = []
    if text.count("\n") > 1:
        warnings.append("multiline_paste")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        warnings.append("control_characters")
    if has_secret_text(text):
        warnings.append("secret_like_text")
    return warnings


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-Id") or new_id("req")


def _websocket_token(websocket: WebSocket) -> str | None:
    query_token = websocket.query_params.get("access_token")
    if query_token:
        return query_token
    header = websocket.headers.get("Authorization") or websocket.headers.get("authorization")
    if header and header.lower().startswith("bearer "):
        return header.split(" ", 1)[1]
    return None
