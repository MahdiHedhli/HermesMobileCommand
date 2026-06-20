"""act-control — Hermes <-> Agentic Control Tower (ACT) control-plane bridge.

An in-process Hermes plugin that makes the operator's phone a first-class control
surface for the real Hermes agent. Two planes:

* MONITORING (Hermes -> ACT, push): session/tool lifecycle hooks upsert the real
  agent / session / mission into the gateway via hermes-local POST /v1/runtime/context
  so the app's dashboard / agents / task-visibility show the REAL agent live.
* CONTROL (ACT -> Hermes):
  - Clearance gate: risky tools block via pre_tool_call until the operator approves
    on the phone (fail-closed).
  - Interactive questions: designated "ask" tools raise an ACT TUA request and block
    until the operator answers on the phone; the answer is returned to the agent.

Safety / sandboxing (unchanged): opt-in via Hermes ``plugins.enabled`` AND a hard env
gate ``ACT_CLEARANCE_ENABLED`` (default OFF) — every hook is a no-op unless enabled, so
installing the files cannot disrupt a live agent. Pushes are hermes-local (loopback);
phone reads/decisions stay device-signed. Redaction: tool name + arg KEYS only.

Stdlib only (urllib) so it runs in any Hermes venv.

Env: ACT_CLEARANCE_ENABLED, ACT_GATEWAY_URL (default http://127.0.0.1:8788/v1),
ACT_CLEARANCE_AGENT_ID (default hermes_agent), ACT_CLEARANCE_AGENT_NAME,
ACT_CLEARANCE_GATED_TOOLS, ACT_QUESTION_TOOLS (default clarify,ask_operator,ask_user),
ACT_CLEARANCE_RISK_FAMILY, ACT_CLEARANCE_TIMEOUT, ACT_CLEARANCE_POLL.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

_DEFAULT_GATEWAY = "http://127.0.0.1:8788/v1"
_DEFAULT_GATED_TOOLS = (
    "terminal,execute_code,shell,execute_command,run_command,bash,"
    "write_file,edit_file,delete_file,apply_patch,browser_submit,send_email,git_push"
)
_DEFAULT_QUESTION_TOOLS = "clarify,ask_operator,ask_user"


def _enabled() -> bool:
    return os.getenv("ACT_CLEARANCE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _gateway() -> str:
    return os.getenv("ACT_GATEWAY_URL", _DEFAULT_GATEWAY).rstrip("/")


def _agent_id() -> str:
    return os.getenv("ACT_CLEARANCE_AGENT_ID", "hermes_agent")


def _agent_name() -> str:
    return os.getenv("ACT_CLEARANCE_AGENT_NAME", "Hermes Agent")


def _control_capabilities() -> List[Dict[str, str]]:
    # Declare the control capabilities so the gateway permits operator-guidance
    # (tua), terminal (tui), browser-assist, and voice handoffs for this agent.
    return [
        {"name": name, "status": "available"}
        for name in ("tua", "tui", "browser_assist", "voice")
    ]


def _csv(name: str, default: str) -> List[str]:
    return [t.strip() for t in os.getenv(name, default).split(",") if t.strip()]


def _is_in(name: str, default: str, tool: str) -> bool:
    items = _csv(name, default)
    return "*" in items or tool in items


def _timeout() -> float:
    try:
        return float(os.getenv("ACT_CLEARANCE_TIMEOUT", "180"))
    except ValueError:
        return 180.0


def _poll() -> float:
    try:
        return float(os.getenv("ACT_CLEARANCE_POLL", "2"))
    except ValueError:
        return 2.0


# --- HTTP (stdlib) ----------------------------------------------------------

def _request(method: str, path: str, payload: Optional[Dict[str, Any]], timeout: float) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(f"{_gateway()}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def _post(path: str, payload: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    return _request("POST", path, payload, timeout)


def _get(path: str, timeout: float = 10.0) -> Dict[str, Any]:
    return _request("GET", path, None, timeout)


# --- redaction --------------------------------------------------------------

def _redacted_payload(tool_name: str, args: Any) -> Dict[str, Any]:
    keys: List[str] = []
    if isinstance(args, dict):
        keys = sorted(str(k) for k in args.keys())
    return {"tool": tool_name, "arg_keys": keys}


def _target_hint(args: Any) -> Optional[str]:
    """A short, non-secret hint about what the tool is acting on (keys/short values)."""
    if not isinstance(args, dict):
        return None
    for key in ("path", "file", "command", "url", "target", "name"):
        val = args.get(key)
        if isinstance(val, str) and val:
            return val[:80]
    return ", ".join(sorted(str(k) for k in args.keys()))[:80] or None


def _block(message: str) -> Dict[str, str]:
    return {"action": "block", "message": f"ACT — {message}"}


# --- monitoring: push real agent/session into ACT ---------------------------

def _post_context(**fields: Any) -> None:
    """Best-effort agent/session/mission upsert. Monitoring fails OPEN (never
    blocks the agent)."""
    if not _enabled():
        return
    payload: Dict[str, Any] = {"agent_id": _agent_id(), "display_name": _agent_name()}
    payload.update({k: v for k, v in fields.items() if v is not None})
    try:
        _post("/runtime/context", payload, timeout=5.0)
    except (urllib.error.URLError, OSError, ValueError):
        pass


def _on_session_start(session_id: str = "", model: str = "", **_: Any) -> None:
    _post_context(
        agent_status="running",
        session_id=session_id or None,
        mission_state="running",
        mission_title="Hermes session" if session_id else None,
        capabilities=_control_capabilities(),
    )


def _on_post_tool_call(
    tool_name: str = "",
    status: str = "",
    session_id: str = "",
    **_: Any,
) -> None:
    _post_context(
        agent_status="error" if status == "error" else "running",
        current_tool=None,
        session_id=session_id or None,
    )


def _on_session_end(
    session_id: str = "",
    completed: bool = False,
    interrupted: bool = False,
    **_: Any,
) -> None:
    # on_session_end fires per turn; only reflect a terminal state when the turn
    # actually completed or was interrupted (avoid flapping the status).
    if not (completed or interrupted):
        return
    _post_context(
        agent_status="idle",
        session_id=session_id or None,
        mission_state="failed" if interrupted and not completed else "completed",
    )


# --- control: interactive question relay (TUA) ------------------------------

def _question_text(tool_name: str, args: Any) -> str:
    if isinstance(args, dict):
        for key in ("question", "prompt", "message", "text", "ask"):
            val = args.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return f"The agent is asking via '{tool_name}'."


def _question_choices(args: Any) -> Optional[List[str]]:
    if isinstance(args, dict):
        choices = args.get("choices") or args.get("options")
        if isinstance(choices, list):
            return [str(c) for c in choices]
    return None


def _relay_question(tool_name: str, args: Any, session_id: str) -> Dict[str, str]:
    """Raise a TUA assistance request and block until the operator answers on the
    phone; return the answer to the agent (delivered via the block message)."""
    reason = _question_text(tool_name, args)
    context: Dict[str, Any] = {"asked_via": tool_name}
    choices = _question_choices(args)
    if choices:
        context["choices"] = choices
    try:
        created = _post(
            "/runtime/tua/requests",
            {
                "agent_id": _agent_id(),
                "session_id": session_id or "hermes_session",
                "reason": reason,
                # A question is not a risky action — use a LOW-risk family so the
                # operator can engage it directly. Non-low-risk handoffs require a
                # prior bound clearance (engage_handoff) and would 403 on engage.
                "risk_family": os.getenv("ACT_QUESTION_RISK_FAMILY", "read_only"),
                "context_redacted": context,
            },
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _block(f"could not reach the operator (fail-closed): {exc}")

    request_id = created.get("request_id")
    if not request_id:
        return _block("gateway did not return a question id (fail-closed)")

    answer = _poll_question_answer(request_id, _timeout(), _poll())
    if answer is None:
        return _block("operator did not answer in time (fail-closed)")
    return {"action": "block", "message": f"The operator answered: {answer}"}


# The createSession initial message the app posts; not the operator's answer.
_SESSION_BOILERPLATE = "Opened from Agentic Control Tower."


def _poll_question_answer(request_id: str, timeout_s: float, poll_s: float) -> Optional[str]:
    """Block until the operator answers. The answer is the operator's typed
    message (the createSession boilerplate is ignored). A session returned/closed
    without a typed reply falls back to the return summary."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            result = _get(f"/runtime/tua/requests/{request_id}/result")
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(poll_s)
            continue
        latest = result.get("latest_session") or {}
        replies = [
            str(message.get("body"))
            for message in (latest.get("messages") or [])
            if message.get("sender_type") == "user"
            and message.get("body")
            and str(message.get("body")).strip() != _SESSION_BOILERPLATE
        ]
        if replies:
            return replies[-1]
        state = latest.get("state") or (result.get("request") or {}).get("state")
        if state in ("returned_to_agent", "closed"):
            return result.get("return_summary") or "Operator returned control without a message."
        time.sleep(poll_s)
    return None


# --- control: clearance gate (existing, fail-closed) ------------------------

def _relay_clearance(tool_name: str, args: Any, session_id: str) -> Optional[Dict[str, str]]:
    risk_family = os.getenv("ACT_CLEARANCE_RISK_FAMILY", "external_effect").strip()
    timeout_s = _timeout()
    try:
        created = _post(
            "/hermes/tools/approval_requested",
            {
                "requested_tool": tool_name,
                "risk_level": "high",
                "risk_family": risk_family,
                "summary": f"Hermes agent requests to run '{tool_name}'.",
                "payload_redacted": _redacted_payload(tool_name, args),
                "agent_id": _agent_id(),
                "session_id": session_id or "hermes_session",
                "expires_in_seconds": int(timeout_s) + 30,
                "suggested_scopes": ["once"],
            },
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return _block(f"gateway unreachable, blocking (fail-closed): {exc}")

    approval_id = created.get("approval_id")
    if not approval_id:
        return _block("gateway did not return an approval id (fail-closed)")

    deadline = time.monotonic() + timeout_s
    poll_s = _poll()
    while time.monotonic() < deadline:
        try:
            status = _post("/hermes/tools/approval_status", {"approval_id": approval_id})
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(poll_s)
            continue
        state = status.get("state")
        if state == "approved":
            return None  # allow
        if state in {"denied", "expired", "cancelled"}:
            return _block(f"operator {state} this action on their phone")
        time.sleep(poll_s)
    return _block("timed out waiting for operator approval (fail-closed)")


# --- the pre_tool_call hook (questions + monitoring + clearance) -------------

def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    session_id: str = "",
    **_: Any,
) -> Optional[Dict[str, str]]:
    if not _enabled() or not tool_name:
        return None

    # 1) Interactive question: route the agent's question to the phone.
    if _is_in("ACT_QUESTION_TOOLS", _DEFAULT_QUESTION_TOOLS, tool_name):
        return _relay_question(tool_name, args, session_id)

    # 2) Monitoring: reflect that the agent is now running this tool (fail-open).
    _post_context(
        agent_status="running",
        current_tool=tool_name,
        current_target=_target_hint(args),
        session_id=session_id or None,
    )

    # 3) Clearance gate for risky tools (fail-closed).
    if _is_in("ACT_CLEARANCE_GATED_TOOLS", _DEFAULT_GATED_TOOLS, tool_name):
        return _relay_clearance(tool_name, args, session_id)

    return None


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    # Make the agent visible immediately (idle) so the fleet shows it before the
    # first tool call. Best-effort; no-op unless enabled.
    threading.Thread(
        target=_post_context,
        kwargs={"agent_status": "idle", "capabilities": _control_capabilities()},
        daemon=True,
    ).start()
