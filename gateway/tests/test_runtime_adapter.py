from __future__ import annotations

from dataclasses import fields
from typing import Any

from fastapi.testclient import TestClient

from hermes_gateway.runtime_adapter import (
    RuntimeAdapter,
    RuntimeClearanceDecision,
    RuntimeClearanceHandle,
    RuntimeClearanceRequest,
    RuntimeHandoffHandle,
    RuntimeHandoffRequest,
    RuntimeHandoffResult,
    RuntimeNotice,
    RuntimeNoticeResult,
    RuntimeWorkState,
)


def test_runtime_adapter_is_protocol_with_neutral_surface() -> None:
    assert getattr(RuntimeAdapter, "_is_protocol", False)

    methods = {
        "record_work_state",
        "publish_notice",
        "request_clearance",
        "check_clearance",
        "cancel_clearance",
        "request_handoff",
        "check_handoff",
    }
    assert methods.issubset(RuntimeAdapter.__dict__)

    protocol_surface = set(methods)
    for dto in (
        RuntimeWorkState,
        RuntimeNotice,
        RuntimeNoticeResult,
        RuntimeClearanceRequest,
        RuntimeClearanceHandle,
        RuntimeClearanceDecision,
        RuntimeHandoffRequest,
        RuntimeHandoffHandle,
        RuntimeHandoffResult,
    ):
        protocol_surface.add(dto.__name__)
        protocol_surface.update(field.name for field in fields(dto))

    surface_text = " ".join(sorted(protocol_surface)).lower()
    for forbidden in ("hermes", "mission", "session", "tool"):
        assert forbidden not in surface_text


def test_app_runtime_adapter_exposes_generic_clearance_and_handoff(client: TestClient) -> None:
    adapter: Any = client.app.state.runtime_adapter

    for method_name in (
        "request_clearance",
        "check_clearance",
        "request_handoff",
        "check_handoff",
    ):
        assert callable(getattr(adapter, method_name))
