from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hermes_gateway.hermes_adapter import HermesToolAdapter
from hermes_gateway.signing import canonical_request
from hermes_gateway.store import SQLiteStore


def main() -> int:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}/v1"
    command = shutil.which("cat") or "/bin/cat"
    with tempfile.TemporaryDirectory(prefix="hmcp-operator-smoke-") as temp_dir:
        temp_path = Path(temp_dir)
        database_path = str(temp_path / "gateway.sqlite3")
        process = _start_gateway(
            port=port,
            base_url=base_url,
            database_path=database_path,
            command=command,
            working_directory=str(temp_path),
        )
        try:
            _wait_for_gateway(base_url, process)
            _grant_tui_capability(database_path)
            paired = _pair_device(base_url)
            adapter = HermesToolAdapter(gateway_base_url=base_url)

            notification = adapter.mobile_notify(
                title="Operator smoke notification",
                body="Hermes needs mobile attention.",
                urgency="high",
                category="approval_required",
                agent_id="agent_mock",
                session_id="sess_mock",
                action_id="act_operator_smoke_notify",
            )
            approval = adapter.approval_requested(
                requested_tool="shell",
                risk_level="high",
                summary="Run a redacted operator smoke command.",
                payload_redacted={"command": "redacted"},
                agent_id="agent_mock",
                session_id="sess_mock",
                expires_in_seconds=300,
                suggested_scopes=["once", "session", "agent"],
                action_id="act_operator_smoke_approval",
            )
            modified_response = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/approvals/{approval['approval_id']}/responses",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={
                    "decision_type": "modified",
                    "alternate_directive": "Run only the dry-run variant.",
                    "constraints": [
                        {
                            "constraint_type": "mode",
                            "value_redacted": {"value": "dry_run"},
                        }
                    ],
                },
            )

            tua_request = _post_json(
                f"{base_url}/tua/requests",
                {
                    "agent_id": "agent_mock",
                    "session_id": "sess_mock",
                    "approval_id": approval["approval_id"],
                    "reason": "Operator clarification needed.",
                    "risk_family": "read_only",
                    "context_redacted": {"source": "operator_smoke"},
                },
            )
            tua_session = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/tua/requests/{tua_request['request_id']}/sessions",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={"initial_message": "Operator is taking a quick look."},
            )
            _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/tua/sessions/{tua_session['assistance_session_id']}/messages",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={"body": "Proceed with the constrained action only."},
            )
            tua_returned = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/tua/sessions/{tua_session['assistance_session_id']}/return-control",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={"summary": "Operator returned control with constraints."},
            )

            browser_session = _post_json(
                f"{base_url}/browser-assistance/sessions",
                {
                    "agent_id": "agent_mock",
                    "session_id": "sess_mock",
                    "approval_id": approval["approval_id"],
                    "reason": "Browser context needs human review.",
                    "risk_family": "read_only",
                    "context_redacted": {"url": "https://example.invalid/review"},
                },
            )
            _signed_json(
                base_url=base_url,
                method="POST",
                api_path=(
                    f"/browser-assistance/sessions/"
                    f"{browser_session['browser_session_id']}/event"
                ),
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={"note": "User reviewed the redacted browser context."},
            )
            browser_returned = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=(
                    f"/browser-assistance/sessions/"
                    f"{browser_session['browser_session_id']}/return-control"
                ),
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={"summary": "Browser assistance returned to agent."},
            )

            voice_session = _signed_json(
                base_url=base_url,
                method="POST",
                api_path="/voice/sessions",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={
                    "agent_id": "agent_mock",
                    "session_id": "sess_mock",
                    "mode": "text_fallback",
                    "risk_family": "read_only",
                },
            )
            _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/voice/sessions/{voice_session['voice_session_id']}/messages",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={"body": "Pause if risk increases.", "input_mode": "text_fallback"},
            )
            voice_closed = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/voice/sessions/{voice_session['voice_session_id']}/close",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )

            tui_session = _signed_json(
                base_url=base_url,
                method="POST",
                api_path="/tui/sessions",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
                body={
                    "agent_id": "agent_mock",
                    "session_context_id": "sess_mock",
                    "risk_level": "high",
                },
            )
            attach = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/tui/sessions/{tui_session['session_id']}/attach-token",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )
            _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/tui/sessions/{tui_session['session_id']}/close",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )

            events = _signed_json(
                base_url=base_url,
                method="GET",
                api_path="/events",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )
            audit = _signed_json(
                base_url=base_url,
                method="GET",
                api_path="/audit/events",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )
            _assert_records(
                modified_response=modified_response,
                notification=notification,
                tua_returned=tua_returned,
                browser_returned=browser_returned,
                voice_closed=voice_closed,
                tui_session=tui_session,
                attach=attach,
                events=events,
                audit=audit,
            )
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "gateway": base_url,
                        "approval_id": approval["approval_id"],
                        "approval_response_id": modified_response[
                            "approval_response_id"
                        ],
                        "tua_session_id": tua_session["assistance_session_id"],
                        "browser_session_id": browser_session["browser_session_id"],
                        "voice_session_id": voice_session["voice_session_id"],
                        "tui_session_id": tui_session["session_id"],
                        "events": len(events["events"]),
                        "audit_events": len(audit["audit_events"]),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def _start_gateway(
    *,
    port: int,
    base_url: str,
    database_path: str,
    command: str,
    working_directory: str,
) -> subprocess.Popen[str]:
    gateway_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    python_path = str(gateway_dir / "src")
    if env.get("PYTHONPATH"):
        python_path = f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    env.update(
        {
            "PYTHONPATH": python_path,
            "HERMES_GATEWAY_DB": database_path,
            "HERMES_NODE_ID": "node_operator_smoke",
            "HERMES_NODE_DISPLAY_NAME": "Operator Smoke Hermes",
            "HERMES_NODE_FINGERPRINT": "operator-smoke-fingerprint",
            "HERMES_GATEWAY_BASE_URL": base_url,
            "HERMES_TUI_ENABLE_LOCAL_PTY": "1",
            "HERMES_TUI_ALLOWED_COMMANDS": command,
            "HERMES_TUI_DEFAULT_COMMAND": command,
            "HERMES_TUI_ALLOWED_WORKING_DIRECTORY": working_directory,
            "HERMES_TUI_ATTACH_TOKEN_TTL_SECONDS": "60",
        }
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "hermes_gateway.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=env,
        cwd=str(gateway_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for_gateway(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"gateway exited before becoming healthy:\n{output}")
        try:
            response = _get_json(f"{base_url}/health")
        except urllib.error.URLError:
            time.sleep(0.2)
            continue
        if response["status"] == "healthy":
            return
    raise RuntimeError("gateway did not become healthy")


def _grant_tui_capability(database_path: str) -> None:
    store = SQLiteStore(database_path)
    agent = store.get_agent("node_operator_smoke", "agent_mock")
    capabilities = [
        item
        for item in agent.get("capabilities", [])
        if item.get("name") != "tui"
    ]
    capabilities.append({"name": "tui", "status": "available"})
    store.upsert_agent({**agent, "capabilities": capabilities})


def _pair_device(base_url: str) -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pairing = _post_json(
        f"{base_url}/pairing/start",
        {
            "display_name": "Operator Smoke Phone",
            "requested_permissions": [
                "read_state",
                "approve",
                "intervene",
                "tui",
                "browser_assist",
                "voice",
            ],
            "clearance_channel": "mobile_signed",
        },
    )
    complete = _post_json(
        f"{base_url}/pairing/complete",
        {
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": _b64url(public_key),
            "device": {
                "device_name": "Operator Smoke Phone",
                "platform": "ios",
                "app_instance_id": "operator-smoke-app",
                "app_version": "0.1.0",
            },
        },
    )
    return {"private_key": private_key, "device_id": complete["device"]["device_id"]}


def _signed_json(
    *,
    base_url: str,
    method: str,
    api_path: str,
    private_key: Ed25519PrivateKey,
    device_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body_bytes = _json_bytes(body) if body is not None else b""
    timestamp = str(int(time.time()))
    nonce = f"operator-smoke-{time.time_ns()}"
    canonical = canonical_request(
        method=method,
        path=f"/v1{api_path}",
        timestamp=timestamp,
        nonce=nonce,
        body=body_bytes,
    )
    signature = private_key.sign(canonical.encode("utf-8"))
    headers = {
        "X-HMCP-Device-Id": device_id,
        "X-HMCP-Timestamp": timestamp,
        "X-HMCP-Nonce": nonce,
        "X-HMCP-Signature": _b64url(signature),
    }
    if body is None:
        return _request_json(f"{base_url}{api_path}", method=method, headers=headers)
    headers["Content-Type"] = "application/json"
    return _request_json(
        f"{base_url}{api_path}",
        method=method,
        headers=headers,
        body=body_bytes,
    )


def _assert_records(
    *,
    modified_response: dict[str, Any],
    notification: dict[str, Any],
    tua_returned: dict[str, Any],
    browser_returned: dict[str, Any],
    voice_closed: dict[str, Any],
    tui_session: dict[str, Any],
    attach: dict[str, Any],
    events: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    if notification["state"] != "queued":
        raise RuntimeError("notification was not queued")
    if modified_response["decision_type"] != "modified":
        raise RuntimeError("modified approval response was not persisted")
    if tua_returned["state"] != "returned_to_agent":
        raise RuntimeError("TUA control was not returned")
    if browser_returned["state"] != "returned_to_agent":
        raise RuntimeError("browser assistance control was not returned")
    if voice_closed["state"] != "closed":
        raise RuntimeError("voice session did not close")
    if tui_session["output_retention_enabled"]:
        raise RuntimeError("TUI output retention must be disabled by default")
    if "attach_token" not in attach:
        raise RuntimeError("TUI attach token was not created")

    event_types = {event["type"] for event in events["events"]}
    expected_events = {
        "notification.created",
        "approval.response.created",
        "tua.returned_to_agent",
        "browser_assistance.returned_to_agent",
        "voice.session.closed",
        "tui.session.state",
    }
    missing_events = expected_events - event_types
    if missing_events:
        raise RuntimeError(f"missing event records: {sorted(missing_events)}")

    audit_types = {event["event_type"] for event in audit["audit_events"]}
    expected_audits = {
        "notification_queued",
        "approval_response_created",
        "tua_returned_to_agent",
        "browser_assistance_returned_to_agent",
        "voice_session_closed",
        "tui_attach_token_created",
    }
    missing_audits = expected_audits - audit_types
    if missing_audits:
        raise RuntimeError(f"missing audit records: {sorted(missing_audits)}")


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _request_json(
        url,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=_json_bytes(payload),
    )


def _get_json(url: str) -> dict[str, Any]:
    return _request_json(url, method="GET")


def _request_json(
    url: str,
    *,
    method: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers or {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    raise SystemExit(main())
