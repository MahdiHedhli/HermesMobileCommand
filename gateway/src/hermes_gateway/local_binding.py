from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from .config import Settings
from .ids import new_id
from .security import content_hash
from .store import SQLiteStore


@dataclass(frozen=True)
class HermesLocalCaller:
    host: str


def verify_hermes_local_request(
    request: Request,
    *,
    store: SQLiteStore,
    settings: Settings,
) -> HermesLocalCaller:
    request_id = request.headers.get("X-Request-Id") or new_id("req")
    host = request.client.host if request.client else ""
    if _is_allowed_hermes_caller(host, settings):
        return HermesLocalCaller(host=host)

    store.append_audit_event(
        event_type="hermes_local_request_rejected",
        actor_type="gateway",
        actor_id="gateway",
        node_id=settings.node_id,
        request_id=request_id,
        payload_redacted={
            "method": request.method,
            "path": request.url.path,
            "caller_hash": content_hash(host) if host else None,
            "reason": "caller_not_loopback_or_allowlisted",
        },
    )
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Hermes-local endpoint requires loopback or configured caller allowlist",
    )


def _is_allowed_hermes_caller(host: str, settings: Settings) -> bool:
    if not host:
        return False
    if host in settings.allowed_hermes_callers:
        return True
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
