from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from .config import Settings
from .ids import new_id
from .local_binding import HermesLocalCaller, verify_hermes_local_request
from .schemas import (
    Agent,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalRequest,
    ApprovalStatusRequest,
    ApprovalStatusResponse,
    AuthTokenSet,
    CompletePairingRequest,
    CompletePairingResponse,
    CreateApprovalRequest,
    CreatePairingSessionRequest,
    Device,
    GatewayHealth,
    HermesApprovalRequestedRequest,
    InterventionRequest,
    InterventionResponse,
    Inventory,
    MobileNotifyRequest,
    Node,
    NodeRegistration,
    Notification,
    PairingSession,
    RefreshTokenRequest,
)
from .security import compare_token, expires_in, has_secret_text, new_token, now_utc, parse_utc
from .signing import VerifiedDevice, verify_signed_request
from .store import SQLiteStore

DEFAULT_PERMISSIONS = ["read_state", "chat", "approve", "intervene"]
MAX_NOTIFICATION_TITLE_CHARS = 120
MAX_NOTIFICATION_BODY_CHARS = 800


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    store = SQLiteStore(resolved_settings.database_path)
    store.initialize()
    _ensure_local_node(store, resolved_settings)
    store.seed_mock_data(node_id=resolved_settings.node_id)

    app = FastAPI(
        title="Hermes Mobile Control Plane Gateway",
        version=resolved_settings.gateway_version,
        description="Self-hosted Hermes Control Gateway skeleton.",
    )
    app.state.settings = resolved_settings
    app.state.store = store

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

    @app.post("/v1/sessions/{session_id}/interventions", response_model=InterventionResponse)
    def intervention_placeholder(
        session_id: str,
        payload: InterventionRequest,
        request: Request,
        device: VerifiedDevice = signed_device_dependency,
    ) -> InterventionResponse:
        store.append_audit_event(
            event_type="intervention_placeholder_requested",
            actor_type="device",
            actor_id=device.device_id,
            node_id=resolved_settings.node_id,
            session_id=session_id,
            request_id=_request_id(request),
            payload_redacted={"type": payload.type, "reason": payload.reason},
        )
        return InterventionResponse(
            intervention_id=payload.intervention_id,
            resulting_state="not_executed_placeholder",
        )

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

    store.resolve_approval(
        approval_id,
        target_state,
        decision_scope=scope,
        decision_actor_device_id=actor_device_id,
        decision_metadata={"decision": decision, "state": target_state},
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
