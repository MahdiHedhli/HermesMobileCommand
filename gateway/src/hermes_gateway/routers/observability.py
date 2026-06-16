from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status

from ..config import Settings
from ..local_binding import HermesLocalCaller
from ..schemas import MobileNotifyRequest, Notification, OperatorSession
from ..signing import VerifiedDevice
from ..store import SQLiteStore


def register_observability_routes(
    *,
    app: FastAPI,
    store: SQLiteStore,
    settings: Settings,
    signed_device_dependency: Any,
    hermes_local_dependency: Any,
    create_mobile_notification: Callable[..., Notification],
    request_id: Callable[[Request], str],
    websocket_token: Callable[[WebSocket], str | None],
) -> None:
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
        return create_mobile_notification(
            store=store,
            settings=settings,
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
        return create_mobile_notification(
            store=store,
            settings=settings,
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
        token = websocket_token(websocket)
        if not token or store.verify_access_token(token) is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        after = websocket.query_params.get("after")
        heartbeat = store.create_event(
            node_id=settings.node_id,
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
                        node_id=settings.node_id,
                        event_type="system.health",
                        payload={"status": "healthy", "reason": "heartbeat"},
                    )
                    await websocket.send_json(event)
                    continue
                if message == "ping":
                    await websocket.send_json(
                        store.create_event(
                            node_id=settings.node_id,
                            event_type="system.health",
                            payload={"status": "healthy", "reason": "pong"},
                        )
                    )
        except WebSocketDisconnect:
            return
