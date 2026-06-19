"""ACT clearance gate — a Hermes plugin that routes risky tool calls through the
Agentic Control Tower (ACT) for operator approval on a paired Secure-Enclave phone.

It registers a ``pre_tool_call`` hook. For tools in the gated set, it asks the ACT
gateway to raise a clearance (``/v1/hermes/tools/approval_requested``), then blocks
the tool until the operator approves on their phone (``/v1/hermes/tools/approval_status``).
FAILS CLOSED: deny, expiry, timeout, or any gateway error blocks the tool.

Safety / sandboxing:
  * Opt-in by Hermes config (``plugins.enabled``) like any user plugin, AND
  * a hard env gate ``ACT_CLEARANCE_ENABLED`` (default OFF) — if unset, every hook
    returns None (no-op), so installing the files cannot affect a live agent.

Configuration (environment):
  ACT_CLEARANCE_ENABLED      "1" to activate (default off — fail-open to no-op so the
                             plugin can't disrupt an agent that hasn't opted in).
  ACT_GATEWAY_URL            ACT gateway base URL (default http://127.0.0.1:8788/v1).
  ACT_CLEARANCE_GATED_TOOLS  CSV of tool names to gate (default: a conservative
                             high-impact set). Use "*" to gate every tool.
  ACT_CLEARANCE_RISK_FAMILY  risk_family to request (default external_effect).
  ACT_CLEARANCE_TIMEOUT      seconds to wait for an operator decision (default 180).
  ACT_CLEARANCE_POLL         poll interval seconds (default 2).

No third-party deps — uses only the standard library so it runs in any Hermes venv.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

_DEFAULT_GATEWAY = "http://127.0.0.1:8788/v1"
_DEFAULT_GATED_TOOLS = (
    "shell,execute_command,run_command,bash,write_file,edit_file,delete_file,"
    "apply_patch,browser_submit,send_email,git_push"
)


def _enabled() -> bool:
    return os.getenv("ACT_CLEARANCE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _gateway() -> str:
    return os.getenv("ACT_GATEWAY_URL", _DEFAULT_GATEWAY).rstrip("/")


def _gated_tools() -> List[str]:
    raw = os.getenv("ACT_CLEARANCE_GATED_TOOLS", _DEFAULT_GATED_TOOLS)
    return [t.strip() for t in raw.split(",") if t.strip()]


def _is_gated(tool_name: str) -> bool:
    tools = _gated_tools()
    return "*" in tools or tool_name in tools


def _post(path: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_gateway()}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def _redacted_payload(tool_name: str, args: Any) -> Dict[str, Any]:
    """Never forward raw argument values (may contain secrets/aircraft text);
    send only the tool name and the argument keys for the operator's context."""
    keys: List[str] = []
    if isinstance(args, dict):
        keys = sorted(str(k) for k in args.keys())
    return {"tool": tool_name, "arg_keys": keys}


def _block(message: str) -> Dict[str, str]:
    return {"action": "block", "message": f"ACT clearance — {message}"}


def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    **_: Any,
) -> Optional[Dict[str, str]]:
    # Default-off: if not explicitly enabled, do nothing (cannot disrupt the agent).
    if not _enabled():
        return None
    if not tool_name or not _is_gated(tool_name):
        return None

    risk_family = os.getenv("ACT_CLEARANCE_RISK_FAMILY", "external_effect").strip()
    try:
        timeout_s = float(os.getenv("ACT_CLEARANCE_TIMEOUT", "180"))
    except ValueError:
        timeout_s = 180.0
    try:
        poll_s = float(os.getenv("ACT_CLEARANCE_POLL", "2"))
    except ValueError:
        poll_s = 2.0

    # 1) Raise the clearance on ACT (operator phone gets it over the event stream).
    try:
        created = _post(
            "/hermes/tools/approval_requested",
            {
                "requested_tool": tool_name,
                "risk_level": "high",
                "risk_family": risk_family,
                "summary": f"Hermes agent requests to run '{tool_name}'.",
                "payload_redacted": _redacted_payload(tool_name, args),
                "agent_id": os.getenv("ACT_CLEARANCE_AGENT_ID", "hermes_agent"),
                "session_id": os.getenv("ACT_CLEARANCE_SESSION_ID", "hermes_session"),
                "expires_in_seconds": int(timeout_s) + 30,
                "suggested_scopes": ["once"],
            },
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _block(f"gateway unreachable, blocking (fail-closed): {exc}")

    approval_id = created.get("approval_id")
    if not approval_id:
        return _block("gateway did not return an approval id (fail-closed)")

    # 2) Block until the operator decides on the phone (fail-closed on timeout).
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            status = _post("/hermes/tools/approval_status", {"approval_id": approval_id})
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(poll_s)
            continue
        state = status.get("state")
        if state == "approved":
            return None  # allow the tool
        if state in {"denied", "expired", "cancelled"}:
            return _block(f"operator {state} this action on their phone")
        time.sleep(poll_s)

    return _block("timed out waiting for operator approval (fail-closed)")


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
