from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from .config import Settings
from .signing import VerifiedDevice
from .store import SQLiteStore

DEVICE_PERMISSION_BY_CAPABILITY = {
    "approvals": "approve",
    "tui": "tui",
    "tua": "intervene",
    "intervene": "intervene",
    "browser_assistance": "browser_assist",
    "voice": "voice",
    "notifications": "read_state",
}

AGENT_OR_NODE_CAPABILITIES = {
    "tui": "tui",
    "tua": "tua",
    "browser_assistance": "browser_assist",
    "voice": "voice",
}


def require_device_capability(
    *,
    store: SQLiteStore,
    settings: Settings,
    device: VerifiedDevice,
    capability: str,
    request_id: str,
    node_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    permission = DEVICE_PERMISSION_BY_CAPABILITY.get(capability)
    if permission and permission in device.permissions:
        return
    if store.has_active_capability_grant(
        subject_type="device",
        subject_id=device.device_id,
        capability=capability,
        node_id=node_id or settings.node_id,
        agent_id=agent_id,
    ):
        return
    _audit_capability_denial(
        store=store,
        settings=settings,
        request_id=request_id,
        actor_type="device",
        actor_id=device.device_id,
        capability=capability,
        node_id=node_id,
        agent_id=agent_id,
        reason="device_lacks_capability",
    )
    if permission:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"device lacks {permission} permission",
        )
    raise HTTPException(status.HTTP_403_FORBIDDEN, f"device lacks {capability} capability")


def require_runtime_capability(
    *,
    store: SQLiteStore,
    settings: Settings,
    capability: str,
    request_id: str,
    actor_id: str,
    node_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    resolved_node_id = node_id or settings.node_id
    if capability in {"approvals", "notifications"}:
        return
    if agent_id and _record_has_capability(
        store=store,
        node_id=resolved_node_id,
        agent_id=agent_id,
        capability=capability,
    ):
        return
    if store.has_active_capability_grant(
        subject_type="runtime",
        subject_id=actor_id,
        capability=capability,
        node_id=resolved_node_id,
        agent_id=agent_id,
    ):
        return
    if agent_id and store.has_active_capability_grant(
        subject_type="agent",
        subject_id=agent_id,
        capability=capability,
        node_id=resolved_node_id,
        agent_id=agent_id,
    ):
        return
    if store.has_active_capability_grant(
        subject_type="node",
        subject_id=resolved_node_id,
        capability=capability,
        node_id=resolved_node_id,
        agent_id=agent_id,
    ):
        return
    _audit_capability_denial(
        store=store,
        settings=settings,
        request_id=request_id,
        actor_type="hermes",
        actor_id=actor_id,
        capability=capability,
        node_id=resolved_node_id,
        agent_id=agent_id,
        reason="runtime_capability_not_granted",
    )
    raise HTTPException(status.HTTP_403_FORBIDDEN, f"runtime lacks {capability} capability")


def _record_has_capability(
    *,
    store: SQLiteStore,
    node_id: str,
    agent_id: str,
    capability: str,
) -> bool:
    capability_name = AGENT_OR_NODE_CAPABILITIES.get(capability, capability)
    records: list[dict[str, Any]] = []
    try:
        records.append(store.get_node(node_id))
    except KeyError:
        pass
    try:
        records.append(store.get_agent(node_id, agent_id))
    except KeyError:
        pass
    for record in records:
        for item in record.get("capabilities", []):
            if item.get("name") == capability_name and item.get("status") == "available":
                return True
    return False


def _audit_capability_denial(
    *,
    store: SQLiteStore,
    settings: Settings,
    request_id: str,
    actor_type: str,
    actor_id: str,
    capability: str,
    reason: str,
    node_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    store.append_audit_event(
        event_type="capability_check_denied",
        actor_type=actor_type,
        actor_id=actor_id,
        node_id=node_id or settings.node_id,
        agent_id=agent_id,
        request_id=request_id,
        payload_redacted={"capability": capability, "reason": reason},
    )
