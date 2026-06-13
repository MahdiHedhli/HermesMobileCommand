from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway" / "src"))

from hermes_gateway.runtime_client import (  # noqa: E402
    HermesRuntimeClient,
    RuntimeClientConfig,
)


@dataclass(frozen=True)
class DemoRuntimeAgentResult:
    mission_id: str
    notification_id: str
    approval_state: str
    approval_scope: str | None
    modified_directive: str | None
    tua_summary: str | None
    browser_summary: str | None
    voice_state: str
    voice_message_count: int


def run_demo_agent(
    client: HermesRuntimeClient,
    *,
    agent_id: str = "agent_demo_runtime",
    session_id: str = "sess_demo_runtime",
    mission_id: str = "mission_demo_runtime",
    timeout_seconds: float = 20.0,
) -> DemoRuntimeAgentResult:
    runtime_capabilities = [
        {"name": "tua", "status": "available"},
        {"name": "browser_assist", "status": "available"},
        {"name": "voice", "status": "available"},
    ]
    client.register_context(
        agent_id=agent_id,
        display_name="Demo Hermes Runtime",
        agent_status="running",
        mission_id=mission_id,
        mission_state="running",
        session_id=session_id,
        mission_title="Demo operator control loop",
        mission_summary="Exercise notification, approvals, TUA, browser assistance, and voice.",
        current_tool="runtime_client.notify",
        capabilities=runtime_capabilities,
    )
    notification = client.notify(
        title="Demo mission started",
        body="Hermes is about to request mobile operator decisions.",
        urgency="high",
        category="system_health",
        agent_id=agent_id,
        session_id=session_id,
        action_id="act_demo_notification",
    )

    client.register_context(
        agent_id=agent_id,
        agent_status="waiting_approval",
        mission_id=mission_id,
        mission_state="waiting_approval",
        session_id=session_id,
        mission_title="Demo operator control loop",
        current_tool="shell",
        current_target="demo-safe-command",
        capabilities=runtime_capabilities,
    )
    approval = client.approval(
        requested_tool="shell",
        risk_level="medium",
        summary="Run the safe demo command after operator approval.",
        payload_redacted={"command": "printf demo"},
        agent_id=agent_id,
        session_id=session_id,
        expires_in_seconds=300,
        suggested_scopes=["once", "session", "agent"],
        action_id="act_demo_approve",
        timeout_seconds=timeout_seconds,
    )
    if not approval.approved:
        client.register_context(
            agent_id=agent_id,
            agent_status="failed",
            mission_id=mission_id,
            mission_state="failed",
            session_id=session_id,
            mission_title="Demo operator control loop",
            mission_summary=f"Approval did not permit continuation: {approval.state}.",
        )
        raise RuntimeError(f"approval did not permit continuation: {approval.state}")

    modified = client.approval(
        requested_tool="browser_submit",
        risk_level="high",
        summary="Submit the demo form, or provide a safer alternate directive.",
        payload_redacted={"url": "https://example.invalid/demo", "form": "redacted"},
        agent_id=agent_id,
        session_id=session_id,
        expires_in_seconds=300,
        suggested_scopes=["once"],
        action_id="act_demo_modified",
        timeout_seconds=timeout_seconds,
    )
    if not modified.modified:
        raise RuntimeError("demo expected a modified approval response")

    client.register_context(
        agent_id=agent_id,
        agent_status="waiting_assistance",
        mission_id=mission_id,
        mission_state="waiting_assistance",
        session_id=session_id,
        mission_title="Demo operator control loop",
        current_tool="tua",
        current_target="operator-summary",
        capabilities=runtime_capabilities,
    )
    assistance = client.request_assistance(
        agent_id=agent_id,
        session_id=session_id,
        reason="Need the operator to choose the safest demo path.",
        context_redacted={"mission_id": mission_id, "source": "demo_runtime_agent"},
        timeout_seconds=timeout_seconds,
    )

    client.register_context(
        agent_id=agent_id,
        agent_status="user_controlling",
        mission_id=mission_id,
        mission_state="user_controlling",
        session_id=session_id,
        mission_title="Demo operator control loop",
        current_tool="browser_assistance",
        current_target="demo-browser-context",
        capabilities=runtime_capabilities,
    )
    browser = client.request_browser_assistance(
        agent_id=agent_id,
        session_id=session_id,
        reason="Operator should inspect the demo browser context and return control.",
        context_redacted={"mission_id": mission_id, "url": "https://example.invalid/demo"},
        timeout_seconds=timeout_seconds,
    )

    voice = client.request_voice(
        agent_id=agent_id,
        session_id=session_id,
        context_redacted={"mission_id": mission_id, "prompt": "Confirm mission completion."},
        timeout_seconds=timeout_seconds,
    )

    client.register_context(
        agent_id=agent_id,
        agent_status="completed",
        mission_id=mission_id,
        mission_state="completed",
        session_id=session_id,
        mission_title="Demo operator control loop",
        mission_summary="Demo mission completed after mobile operator handoffs.",
        current_tool=None,
        current_target=None,
        capabilities=runtime_capabilities,
    )
    return DemoRuntimeAgentResult(
        mission_id=mission_id,
        notification_id=notification.notification_id,
        approval_state=approval.state,
        approval_scope=approval.selected_scope,
        modified_directive=modified.alternate_directive,
        tua_summary=assistance.return_summary,
        browser_summary=browser.return_summary,
        voice_state=voice.state,
        voice_message_count=len(voice.transcript),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Hermes Mobile Control Plane demo runtime.")
    parser.add_argument("--gateway", default="http://127.0.0.1:8787/v1")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    client = HermesRuntimeClient(
        RuntimeClientConfig(base_url=args.gateway, timeout_seconds=5.0)
    )
    result = run_demo_agent(client, timeout_seconds=args.timeout)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
