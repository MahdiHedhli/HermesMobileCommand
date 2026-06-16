from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .config import Settings
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
    engage: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    del (
        store,
        settings,
        handoff_kind,
        handoff_ref,
        node_id,
        agent_id,
        work_ref,
        risk_family,
        clearance_ref,
        request_id,
        actor_type,
        actor_id,
    )
    return engage()
