from __future__ import annotations

import base64
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hermes_gateway.app import create_app
from hermes_gateway.config import Settings
from hermes_gateway.signing import canonical_request


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="hmcp-runtime-smoke-") as temp_dir:
        settings = Settings(
            node_id="node_runtime_smoke",
            node_display_name="Runtime Smoke Hermes",
            node_fingerprint="runtime-smoke-fingerprint",
            gateway_base_url="http://127.0.0.1:8787/v1",
            database_path=str(Path(temp_dir) / "gateway.sqlite3"),
            pairing_ttl_seconds=60,
        )
        with TestClient(create_app(settings), client=("127.0.0.1", 50000)) as client:
            paired = _pair_device(client)
            context = _post_json(
                client,
                "/v1/runtime/context",
                {
                    "agent_id": "agent_runtime_smoke",
                    "display_name": "Runtime Smoke Agent",
                    "agent_status": "running",
                    "mission_id": "mission_runtime_smoke",
                    "mission_state": "running",
                    "session_id": "sess_runtime_smoke",
                    "mission_title": "Runtime smoke mission",
                    "mission_summary": "Local runtime integration smoke.",
                    "current_tool": "shell",
                    "capabilities": [
                        {"name": "tua", "status": "available"},
                        {"name": "browser_assist", "status": "available"},
                        {"name": "voice", "status": "available"},
                    ],
                },
            )
            notification = _post_json(
                client,
                "/v1/runtime/notifications",
                {
                    "title": "Runtime smoke notification",
                    "body": "Hermes runtime needs mobile attention.",
                    "urgency": "high",
                    "category": "approval_required",
                    "agent_id": "agent_runtime_smoke",
                    "session_id": "sess_runtime_smoke",
                    "action_id": "act_runtime_smoke_notify",
                },
                expected_status=202,
            )
            approval = _runtime_approval(client, "act_runtime_smoke_approve")
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/approvals/{approval['approval_id']}/approve_once",
            )
            approval_result = _get_json(
                client,
                f"/v1/runtime/approvals/{approval['approval_id']}/result",
            )

            modified_approval = _runtime_approval(client, "act_runtime_smoke_modified")
            modified_response = _signed_json(
                client,
                paired,
                "POST",
                f"/v1/approvals/{modified_approval['approval_id']}/responses",
                {
                    "decision_type": "modified",
                    "alternate_directive": "Run the dry-run variant only.",
                    "constraints": [
                        {
                            "constraint_type": "mode",
                            "value_redacted": {"value": "dry_run"},
                        }
                    ],
                },
            )
            modified_result = _get_json(
                client,
                f"/v1/runtime/approvals/{modified_approval['approval_id']}/result",
            )

            tua_request = _post_json(
                client,
                "/v1/runtime/tua/requests",
                {
                    "agent_id": "agent_runtime_smoke",
                    "session_id": "sess_runtime_smoke",
                    "approval_id": modified_approval["approval_id"],
                    "reason": "Operator guidance needed.",
                    "context_redacted": {"mission_id": "mission_runtime_smoke"},
                },
                expected_status=201,
            )
            tua_session = _signed_json(
                client,
                paired,
                "POST",
                f"/v1/tua/requests/{tua_request['request_id']}/sessions",
                {"initial_message": "Operator is reviewing the request."},
            )
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/tua/sessions/{tua_session['assistance_session_id']}/messages",
                {"body": "Use the constrained path only."},
            )
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/tua/sessions/{tua_session['assistance_session_id']}/return-control",
                {"summary": "Returned with constrained guidance."},
            )
            tua_result = _get_json(
                client,
                f"/v1/runtime/tua/requests/{tua_request['request_id']}/result",
            )

            browser_session = _post_json(
                client,
                "/v1/runtime/browser-assistance/sessions",
                {
                    "agent_id": "agent_runtime_smoke",
                    "session_id": "sess_runtime_smoke",
                    "approval_id": modified_approval["approval_id"],
                    "reason": "Browser context requires human review.",
                    "context_redacted": {
                        "mission_id": "mission_runtime_smoke",
                        "url": "https://example.invalid/review",
                    },
                },
                expected_status=201,
            )
            _signed_json(
                client,
                paired,
                "POST",
                (
                    "/v1/browser-assistance/sessions/"
                    f"{browser_session['browser_session_id']}/event"
                ),
                {"note": "Reviewed redacted browser context."},
            )
            _signed_json(
                client,
                paired,
                "POST",
                (
                    "/v1/browser-assistance/sessions/"
                    f"{browser_session['browser_session_id']}/return-control"
                ),
                {"summary": "Browser context reviewed and returned."},
            )
            browser_result = _get_json(
                client,
                (
                    "/v1/runtime/browser-assistance/sessions/"
                    f"{browser_session['browser_session_id']}/result"
                ),
            )

            voice_session = _post_json(
                client,
                "/v1/runtime/voice/sessions",
                {
                    "agent_id": "agent_runtime_smoke",
                    "session_id": "sess_runtime_smoke",
                    "mode": "text_fallback",
                    "context_redacted": {"mission_id": "mission_runtime_smoke"},
                },
                expected_status=201,
            )
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/voice/sessions/{voice_session['voice_session_id']}/messages",
                {"body": "Proceed after approval.", "input_mode": "text_fallback"},
            )
            _signed_json(
                client,
                paired,
                "POST",
                f"/v1/voice/sessions/{voice_session['voice_session_id']}/close",
            )
            voice_result = _get_json(
                client,
                f"/v1/runtime/voice/sessions/{voice_session['voice_session_id']}/result",
            )

            events = _signed_json(client, paired, "GET", "/v1/events")
            audit = _signed_json(client, paired, "GET", "/v1/audit/events")

            _assert_smoke(
                context=context,
                notification=notification,
                approval_result=approval_result,
                modified_response=modified_response,
                modified_result=modified_result,
                tua_result=tua_result,
                browser_result=browser_result,
                voice_result=voice_result,
                events=events,
                audit=audit,
            )
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "node_id": settings.node_id,
                        "approval_id": approval["approval_id"],
                        "modified_approval_id": modified_approval["approval_id"],
                        "tua_request_id": tua_request["request_id"],
                        "browser_session_id": browser_session["browser_session_id"],
                        "voice_session_id": voice_session["voice_session_id"],
                        "events": len(events["events"]),
                        "audit_events": len(audit["audit_events"]),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
    return 0


def _runtime_approval(client: TestClient, action_id: str) -> dict[str, Any]:
    return _post_json(
        client,
        "/v1/runtime/approvals",
        {
            "requested_tool": "shell",
            "risk_level": "high",
            "risk_family": "destructive",
            "summary": "Runtime smoke shell action.",
            "payload_redacted": {"command": "redacted"},
            "agent_id": "agent_runtime_smoke",
            "session_id": "sess_runtime_smoke",
            "expires_in_seconds": 300,
            "suggested_scopes": ["once", "session", "agent"],
            "action_id": action_id,
        },
        expected_status=201,
    )


def _pair_device(client: TestClient) -> dict[str, Any]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    start = _post_json(
        client,
        "/v1/pairing/start",
        {
            "display_name": "Runtime Smoke Phone",
            "requested_permissions": [
                "read_state",
                "approve",
                "intervene",
                "browser_assist",
                "voice",
            ],
        },
        expected_status=201,
    )
    paired = _post_json(
        client,
        "/v1/pairing/complete",
        {
            "pairing_id": start["pairing_id"],
            "challenge_response": start["pairing_token"],
            "device_public_key": _b64url(public_key),
            "device": {
                "device_name": "Runtime Smoke Phone",
                "platform": "ios",
                "app_instance_id": "runtime-smoke",
                "app_version": "0.1.0",
            },
        },
    )
    return {
        "private_key": private_key,
        "device_id": paired["device"]["device_id"],
    }


def _post_json(
    client: TestClient,
    path: str,
    body: dict[str, Any],
    *,
    expected_status: int = 200,
) -> dict[str, Any]:
    response = client.post(path, json=body)
    assert response.status_code == expected_status, response.text
    return response.json()


def _get_json(client: TestClient, path: str) -> dict[str, Any]:
    response = client.get(path)
    assert response.status_code == 200, response.text
    return response.json()


def _signed_json(
    client: TestClient,
    paired: dict[str, Any],
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    encoded = (
        json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if body
        else b""
    )
    timestamp = str(int(time.time()))
    nonce = f"nonce-{time.time_ns()}"
    canonical = canonical_request(
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body=encoded,
    )
    signature = paired["private_key"].sign(canonical.encode("utf-8"))
    response = client.request(
        method,
        path,
        content=encoded,
        headers={
            "Content-Type": "application/json",
            "X-HMCP-Device-Id": paired["device_id"],
            "X-HMCP-Timestamp": timestamp,
            "X-HMCP-Nonce": nonce,
            "X-HMCP-Signature": _b64url(signature),
        },
    )
    assert response.status_code < 400, response.text
    return response.json() if response.content else {}


def _assert_smoke(**records: dict[str, Any]) -> None:
    assert records["context"]["mission"]["state"] == "running"
    assert records["notification"]["state"] == "queued"
    assert records["approval_result"]["state"] == "approved"
    assert records["approval_result"]["selected_scope"] == "once"
    assert records["modified_response"]["decision_type"] == "modified"
    assert records["modified_result"]["responses"][0]["decision_type"] == "modified"
    assert records["tua_result"]["latest_session"]["state"] == "returned_to_agent"
    assert records["browser_result"]["session"]["state"] == "returned_to_agent"
    assert records["voice_result"]["session"]["state"] == "closed"
    event_types = {event["type"] for event in records["events"]["events"]}
    assert "approval.requested" in event_types
    assert "tua.returned_to_agent" in event_types
    assert "browser_assistance.returned_to_agent" in event_types
    assert "voice.session.closed" in event_types
    audit_types = {event["event_type"] for event in records["audit"]["audit_events"]}
    assert "approval_decision" in audit_types
    assert "tua_returned_to_agent" in audit_types
    assert "browser_assistance_returned_to_agent" in audit_types
    assert "voice_session_closed" in audit_types


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


if __name__ == "__main__":
    raise SystemExit(main())
