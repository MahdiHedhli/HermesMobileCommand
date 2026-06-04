from __future__ import annotations

import base64
import json
import os
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


def main() -> int:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}/v1"
    with tempfile.TemporaryDirectory(prefix="hmcp-smoke-") as temp_dir:
        database_path = str(Path(temp_dir) / "gateway.sqlite3")
        process = _start_gateway(port=port, database_path=database_path)
        try:
            _wait_for_gateway(base_url, process)
            _post_json(
                f"{base_url}/nodes/register",
                {
                    "node_id": "node_smoke",
                    "display_name": "Smoke Hermes",
                    "environment": "homelab",
                    "gateway_base_url": base_url,
                    "node_fingerprint": "smoke-fingerprint",
                    "gateway_version": "0.1.0",
                    "hermes_version": "smoke",
                    "tags": ["smoke"],
                },
            )
            paired = _pair_device(base_url)
            adapter = HermesToolAdapter(gateway_base_url=base_url)
            notification = adapter.mobile_notify(
                title="Approval required",
                body="Hermes needs a mobile decision.",
                urgency="high",
                category="approval_required",
                agent_id="agent_mock",
                session_id="sess_mock",
                action_id="act_smoke_notify",
            )
            approval = adapter.approval_requested(
                requested_tool="shell",
                risk_level="high",
                summary="Run a redacted shell command.",
                payload_redacted={"command": "redacted"},
                agent_id="agent_mock",
                session_id="sess_mock",
                expires_in_seconds=300,
                suggested_scopes=["once"],
                action_id="act_smoke_approval",
            )
            pending = _signed_json(
                base_url=base_url,
                method="GET",
                api_path="/approvals?state=pending",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )
            if approval["approval_id"] not in {
                item["approval_id"] for item in pending["approvals"]
            }:
                raise RuntimeError("Hermes-created approval was not visible to mobile")

            decision = _signed_json(
                base_url=base_url,
                method="POST",
                api_path=f"/approvals/{approval['approval_id']}/approve_once",
                private_key=paired["private_key"],
                device_id=paired["device_id"],
            )
            status = adapter.approval_status(approval_id=approval["approval_id"])
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
            _assert_records(notification, approval, decision, status, events, audit)
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "gateway": base_url,
                        "notification_id": notification["notification_id"],
                        "approval_id": approval["approval_id"],
                        "decision_state": decision["state"],
                        "approval_status": status["state"],
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


def _start_gateway(*, port: int, database_path: str) -> subprocess.Popen[str]:
    gateway_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "HERMES_GATEWAY_DB": database_path,
            "HERMES_NODE_ID": "node_smoke",
            "HERMES_NODE_DISPLAY_NAME": "Smoke Hermes",
            "HERMES_NODE_FINGERPRINT": "smoke-fingerprint",
            "HERMES_GATEWAY_BASE_URL": f"http://127.0.0.1:{port}/v1",
        }
    )
    python_path = str(gateway_dir / "src")
    if env.get("PYTHONPATH"):
        python_path = f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONPATH"] = python_path
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


def _pair_device(base_url: str) -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pairing = _post_json(
        f"{base_url}/pairing/start",
        {
            "display_name": "Smoke Phone",
            "requested_permissions": ["read_state", "approve", "intervene"],
        },
    )
    complete = _post_json(
        f"{base_url}/pairing/complete",
        {
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": _b64url(public_key),
            "device": {
                "device_name": "Smoke Phone",
                "platform": "ios",
                "app_instance_id": "smoke-app",
                "app_version": "0.1.0",
            },
        },
    )
    return {
        "private_key": private_key,
        "device_id": complete["device"]["device_id"],
    }


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
    nonce = f"smoke-{time.time_ns()}"
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
    notification: dict[str, Any],
    approval: dict[str, Any],
    decision: dict[str, Any],
    status: dict[str, Any],
    events: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    if notification["state"] != "queued":
        raise RuntimeError("notification was not queued")
    if approval["state"] != "pending":
        raise RuntimeError("approval was not initially pending")
    if decision["state"] != "approved":
        raise RuntimeError("signed mobile approval did not approve")
    if status["state"] != "approved" or status["selected_scope"] != "once":
        raise RuntimeError("Hermes approval_status did not observe approved scope")
    event_types = {event["type"] for event in events["events"]}
    if "notification.created" not in event_types or "approval.requested" not in event_types:
        raise RuntimeError("expected event records were missing")
    audit_types = {event["event_type"] for event in audit["audit_events"]}
    if "notification_queued" not in audit_types or "approval_decision" not in audit_types:
        raise RuntimeError("expected audit records were missing")


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
