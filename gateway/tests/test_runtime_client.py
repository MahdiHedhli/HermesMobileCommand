from __future__ import annotations

from typing import Any

import pytest

from hermes_gateway.runtime_client import (
    HermesRuntimeClient,
    RuntimeClientConfig,
    RuntimeClientError,
)


def test_runtime_client_requires_loopback_by_default() -> None:
    with pytest.raises(RuntimeClientError):
        HermesRuntimeClient(RuntimeClientConfig(base_url="http://192.0.2.10:8787/v1"))


def test_runtime_client_waits_for_modified_approval_response() -> None:
    calls: list[tuple[str, str]] = []
    polls = {"count": 0}

    def transport(
        method: str,
        path: str,
        body: dict[str, Any] | None,
        _timeout: float,
    ) -> dict[str, Any]:
        calls.append((method, path))
        if path == "/runtime/approvals":
            assert body
            assert body["action_id"] == "act_client_modified"
            return {
                "approval_id": "approval_client",
                "action_id": "act_client_modified",
                "state": "pending",
            }
        if path == "/runtime/approvals/approval_client/result":
            polls["count"] += 1
            responses = []
            if polls["count"] > 1:
                responses = [
                    {
                        "approval_response_id": "resp_client",
                        "approval_id": "approval_client",
                        "decision_type": "modified",
                        "created_by_device_id": "device_client",
                        "alternate_directive": "Run in dry-run mode.",
                        "constraints": [
                            {
                                "constraint_type": "mode",
                                "value_redacted": {"value": "dry_run"},
                            }
                        ],
                        "created_at": "2026-06-13T00:00:00Z",
                    }
                ]
            return {
                "approval_id": "approval_client",
                "state": "pending",
                "selected_scope": None,
                "decision_metadata": {},
                "responses": responses,
            }
        raise AssertionError(f"unexpected request {method} {path}")

    client = HermesRuntimeClient(
        RuntimeClientConfig(poll_interval_seconds=0.001),
        transport=transport,
    )

    decision = client.approval(
        requested_tool="browser_submit",
        risk_level="high",
        summary="Submit form.",
        payload_redacted={"url": "redacted"},
        agent_id="agent_client",
        session_id="sess_client",
        action_id="act_client_modified",
        timeout_seconds=1,
    )

    assert decision.modified
    assert decision.alternate_directive == "Run in dry-run mode."
    assert decision.constraints[0]["value_redacted"]["value"] == "dry_run"
    assert calls[0] == ("POST", "/runtime/approvals")
