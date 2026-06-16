from __future__ import annotations

import base64
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "gateway" / "src"))
sys.path.insert(0, str(ROOT))

from examples.demo_runtime_agent import run_demo_agent  # noqa: E402

from hermes_gateway.app import create_app  # noqa: E402
from hermes_gateway.config import Settings  # noqa: E402
from hermes_gateway.runtime_client import HermesRuntimeClient, RuntimeClientConfig  # noqa: E402
from hermes_gateway.signing import canonical_request  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="hmcp-real-hermes-e2e-") as temp_dir:
        settings = Settings(
            node_id="node_real_hermes_e2e",
            node_display_name="Real Hermes E2E Gateway",
            node_fingerprint="real-hermes-e2e-fingerprint",
            gateway_base_url="http://127.0.0.1:8787/v1",
            database_path=str(Path(temp_dir) / "gateway.sqlite3"),
            pairing_ttl_seconds=60,
        )
        with TestClient(create_app(settings), client=("127.0.0.1", 50000)) as client:
            paired = _pair_device(client)
            runtime_client = HermesRuntimeClient(
                RuntimeClientConfig(timeout_seconds=2.0, poll_interval_seconds=0.05),
                transport=_test_client_transport(client),
            )

            result_box: dict[str, Any] = {}
            error_box: dict[str, BaseException] = {}
            agent_thread = threading.Thread(
                target=_run_agent,
                args=(runtime_client, result_box, error_box),
                daemon=True,
            )
            agent_thread.start()
            _drive_mobile_operator(client, paired, error_box)
            agent_thread.join(timeout=5)
            if agent_thread.is_alive():
                raise RuntimeError("demo runtime agent did not finish")
            if error_box:
                raise RuntimeError("demo runtime agent failed") from error_box["error"]

            result = result_box["result"]
            missions = _signed_json(client, paired, "GET", "/v1/missions")
            mission = next(
                item
                for item in missions["missions"]
                if item["mission_id"] == result.mission_id
            )
            if mission["state"] != "completed":
                raise AssertionError(f"mission did not complete: {mission}")

            events = _signed_json(client, paired, "GET", "/v1/events")
            audits = _signed_json(client, paired, "GET", "/v1/audit/events")
            operator_sessions = _signed_json(client, paired, "GET", "/v1/operator-sessions")
            if len(events["events"]) < 12:
                raise AssertionError("expected runtime/mobile event records")
            if len(audits["audit_events"]) < 8:
                raise AssertionError("expected runtime/mobile audit records")
            session_types = {
                item["session_type"] for item in operator_sessions["operator_sessions"]
            }
            required_sessions = {"tua", "browser_assistance", "voice"}
            if not required_sessions.issubset(session_types):
                raise AssertionError(f"missing operator sessions: {session_types}")

            print(
                json.dumps(
                    {
                        "mission_state": mission["state"],
                        "notification_id": result.notification_id,
                        "approval_scope": result.approval_scope,
                        "modified_directive": result.modified_directive,
                        "tua_summary": result.tua_summary,
                        "browser_summary": result.browser_summary,
                        "voice_state": result.voice_state,
                        "events": len(events["events"]),
                        "audit_events": len(audits["audit_events"]),
                        "operator_session_types": sorted(session_types),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
    return 0


def _run_agent(
    runtime_client: HermesRuntimeClient,
    result_box: dict[str, Any],
    error_box: dict[str, BaseException],
) -> None:
    try:
        result_box["result"] = run_demo_agent(runtime_client, timeout_seconds=10)
    except BaseException as exc:  # noqa: BLE001 - preserve thread failure for main.
        error_box["error"] = exc


def _drive_mobile_operator(
    client: TestClient,
    paired: dict[str, Any],
    error_box: dict[str, BaseException],
) -> None:
    handled: set[str] = set()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if error_box:
            raise RuntimeError("demo runtime agent failed") from error_box["error"]
        _resolve_pending_approvals(client, paired, handled)
        _resolve_tua_requests(client, paired, handled)
        _resolve_browser_sessions(client, paired, handled)
        _resolve_voice_sessions(client, paired, handled)
        if _mission_completed(client, paired):
            return
        time.sleep(0.05)
    raise RuntimeError("mobile operator automation timed out")


def _resolve_pending_approvals(
    client: TestClient, paired: dict[str, Any], handled: set[str]
) -> None:
    pending = _signed_json(client, paired, "GET", "/v1/approvals", query={"state": "pending"})
    for approval in pending["approvals"]:
        action_id = approval["action_id"]
        approval_id = approval["approval_id"]
        if action_id in handled:
            continue
        if action_id == "act_demo_approve":
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/approvals/{approval_id}/responses",
                {
                    "decision_type": "approve_session",
                    "params_fingerprint": approval["params_fingerprint"],
                },
            )
            handled.add(action_id)
        elif action_id == "act_demo_modified":
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/approvals/{approval_id}/responses",
                {
                    "decision_type": "modified",
                    "alternate_directive": "Use the read-only demo path and do not submit.",
                    "constraints": [
                        {
                            "constraint_type": "mode",
                            "value_redacted": {"value": "read_only"},
                        }
                    ],
                },
            )
            handled.add(action_id)


def _resolve_tua_requests(client: TestClient, paired: dict[str, Any], handled: set[str]) -> None:
    requests = _signed_json(client, paired, "GET", "/v1/tua/requests")
    for item in requests["requests"]:
        key = f"tua:{item['request_id']}"
        if item["state"] not in {"requested", "waiting_on_user"} or key in handled:
            continue
        session = _signed_json(
            client,
            paired,
            "POST",
            f"/v1/tua/requests/{item['request_id']}/sessions",
            {"initial_message": "Operator is taking the demo handoff."},
        )
        session_id = session["assistance_session_id"]
        _signed_json(
            client,
            paired,
            "POST",
            f"/v1/tua/sessions/{session_id}/messages",
            {"body": "Proceed with the constrained read-only path."},
        )
        _signed_json(
            client,
            paired,
            "POST",
            f"/v1/tua/sessions/{session_id}/return-control",
            {"summary": "Operator selected the constrained read-only path."},
        )
        handled.add(key)


def _resolve_browser_sessions(
    client: TestClient, paired: dict[str, Any], handled: set[str]
) -> None:
    sessions = _signed_json(client, paired, "GET", "/v1/browser-assistance/sessions")
    for session in sessions["sessions"]:
        session_id = session["browser_session_id"]
        key = f"browser:{session_id}"
        if session["state"] not in {"requested", "active"} or key in handled:
            continue
        _signed_json(
            client,
            paired,
            "POST",
            f"/v1/browser-assistance/sessions/{session_id}/event",
            {"note": "Checked the demo browser context."},
        )
        _signed_json(
            client,
            paired,
            "POST",
            f"/v1/browser-assistance/sessions/{session_id}/return-control",
            {"summary": "Browser context reviewed; no submit action taken."},
        )
        handled.add(key)


def _resolve_voice_sessions(
    client: TestClient, paired: dict[str, Any], handled: set[str]
) -> None:
    sessions = _signed_json(
        client,
        paired,
        "GET",
        "/v1/operator-sessions",
        query={"session_type": "voice"},
    )
    for session in sessions["operator_sessions"]:
        session_id = session["session_id"]
        key = f"voice:{session_id}"
        if session["state"] != "active" or key in handled:
            continue
        _signed_json(
            client,
            paired,
            "POST",
            f"/v1/voice/sessions/{session_id}/messages",
            {"body": "Confirmed. Complete the demo mission.", "input_mode": "text_fallback"},
        )
        _signed_json(client, paired, "POST", f"/v1/voice/sessions/{session_id}/close")
        handled.add(key)


def _mission_completed(client: TestClient, paired: dict[str, Any]) -> bool:
    missions = _signed_json(client, paired, "GET", "/v1/missions")
    return any(
        item["mission_id"] == "mission_demo_runtime" and item["state"] == "completed"
        for item in missions["missions"]
    )


def _test_client_transport(client: TestClient):
    def transport(
        method: str,
        path: str,
        body: dict[str, Any] | None,
        _timeout: float,
    ) -> dict[str, Any]:
        response = client.request(method, f"/v1{path}", json=body)
        if response.status_code >= 400:
            raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text}")
        return response.json() if response.content else {}

    return transport


def _pair_device(client: TestClient) -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    start = client.post(
        "/v1/pairing/start",
        json={
            "display_name": "E2E Operator Phone",
            "requested_permissions": [
                "read_state",
                "approve",
                "intervene",
                "browser_assist",
                "voice",
            ],
            "clearance_channel": "mobile_signed",
        },
    )
    _assert_status(start, 201)
    pairing = start.json()
    complete = client.post(
        "/v1/pairing/complete",
        json={
            "pairing_id": pairing["pairing_id"],
            "challenge_response": pairing["pairing_token"],
            "device_public_key": _b64url(public_key),
            "device": {
                "device_name": "E2E Operator Phone",
                "platform": "ios",
                "app_instance_id": "real-hermes-e2e",
                "app_version": "0.1.0",
            },
        },
    )
    _assert_status(complete, 200)
    paired = complete.json()
    paired["private_key"] = private_key
    return paired


def _signed_json(
    client: TestClient,
    paired: dict[str, Any],
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    *,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    encoded_query = ""
    if query:
        encoded_query = "?" + urllib_parse_urlencode(query)
    signed_path = f"{path}{encoded_query}"
    body = _json_bytes(json_body) if json_body is not None else b""
    headers = _signature_headers(
        private_key=paired["private_key"],
        device_id=paired["device"]["device_id"],
        method=method,
        path=signed_path,
        body=body,
    )
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    response = client.request(method, signed_path, content=body, headers=headers)
    _assert_status(response, 200 if method == "GET" else None)
    return response.json() if response.content else {}


def urllib_parse_urlencode(query: dict[str, str]) -> str:
    from urllib.parse import urlencode

    return urlencode(query)


def _signature_headers(
    *,
    private_key: Ed25519PrivateKey,
    device_id: str,
    method: str,
    path: str,
    body: bytes = b"",
) -> dict[str, str]:
    timestamp_text = str(int(time.time()))
    nonce_text = f"nonce-{time.time_ns()}"
    canonical = canonical_request(
        method=method,
        path=path,
        timestamp=timestamp_text,
        nonce=nonce_text,
        body=body,
    )
    signature = private_key.sign(canonical.encode("utf-8"))
    return {
        "X-HMCP-Device-Id": device_id,
        "X-HMCP-Timestamp": timestamp_text,
        "X-HMCP-Nonce": nonce_text,
        "X-HMCP-Signature": _b64url(signature),
    }


def _json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _assert_status(response: Any, expected: int | None) -> None:
    if expected is None:
        if response.status_code < 200 or response.status_code >= 300:
            raise AssertionError(f"unexpected status {response.status_code}: {response.text}")
        return
    if response.status_code != expected:
        raise AssertionError(f"expected {expected}, got {response.status_code}: {response.text}")


if __name__ == "__main__":
    raise SystemExit(main())
