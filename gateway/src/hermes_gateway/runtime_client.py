from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

JsonObject = dict[str, Any]
RuntimeTransport = Callable[[str, str, JsonObject | None, float], JsonObject]


class RuntimeClientError(RuntimeError):
    pass


class RuntimeClientTimeout(RuntimeClientError):
    pass


@dataclass(frozen=True)
class ApprovalDecision:
    approval_id: str
    state: str
    selected_scope: str | None
    decision_type: str | None
    alternate_directive: str | None
    user_message: str | None
    constraints: list[JsonObject]
    raw: JsonObject

    @property
    def approved(self) -> bool:
        return self.state == "approved"

    @property
    def denied(self) -> bool:
        return self.state == "denied"

    @property
    def modified(self) -> bool:
        return self.decision_type == "modified"

    @property
    def needs_info(self) -> bool:
        return self.decision_type == "needs_info"


@dataclass(frozen=True)
class AssistanceResult:
    request_id: str
    state: str
    return_summary: str | None
    latest_session: JsonObject | None
    messages: list[JsonObject]
    raw: JsonObject


@dataclass(frozen=True)
class BrowserAssistanceResult:
    session_id: str
    state: str
    return_summary: str | None
    user_action_notes: list[str]
    raw: JsonObject


@dataclass(frozen=True)
class VoiceInteractionResult:
    session_id: str
    state: str
    transcript: list[JsonObject]
    raw: JsonObject


@dataclass(frozen=True)
class NotificationResult:
    notification_id: str
    state: str
    urgency: str
    category: str
    raw: JsonObject


@dataclass(frozen=True)
class RuntimeClientConfig:
    base_url: str = "http://127.0.0.1:8787/v1"
    timeout_seconds: float = 5.0
    retry_attempts: int = 3
    retry_backoff_seconds: float = 0.2
    poll_interval_seconds: float = 0.25
    allow_non_loopback: bool = False


@dataclass
class HermesRuntimeClient:
    config: RuntimeClientConfig = field(default_factory=RuntimeClientConfig)
    transport: RuntimeTransport | None = None

    def __post_init__(self) -> None:
        self._base_url = self.config.base_url.rstrip("/")
        if self.transport is None and not self.config.allow_non_loopback:
            _assert_loopback_url(self._base_url)

    def register_context(
        self,
        *,
        agent_id: str,
        display_name: str | None = None,
        agent_status: str = "running",
        mission_id: str | None = None,
        mission_state: str = "running",
        session_id: str | None = None,
        mission_title: str | None = None,
        mission_summary: str | None = None,
        current_tool: str | None = None,
        current_target: str | None = None,
        node_id: str | None = None,
        capabilities: list[JsonObject] | None = None,
    ) -> JsonObject:
        return self._request(
            "POST",
            "/runtime/context",
            {
                "agent_id": agent_id,
                "display_name": display_name,
                "agent_status": agent_status,
                "mission_id": mission_id,
                "mission_state": mission_state,
                "session_id": session_id,
                "mission_title": mission_title,
                "mission_summary": mission_summary,
                "current_tool": current_tool,
                "current_target": current_target,
                "node_id": node_id,
                "capabilities": capabilities or [],
            },
        )

    def notify(
        self,
        *,
        title: str,
        body: str,
        urgency: str,
        category: str,
        agent_id: str,
        session_id: str,
        action_id: str | None = None,
        deep_link: str | None = None,
    ) -> NotificationResult:
        result = self._request(
            "POST",
            "/runtime/notifications",
            {
                "title": title,
                "body": body,
                "urgency": urgency,
                "category": category,
                "agent_id": agent_id,
                "session_id": session_id,
                "action_id": action_id,
                "deep_link": deep_link,
            },
        )
        return NotificationResult(
            notification_id=result["notification_id"],
            state=result["state"],
            urgency=result["urgency"],
            category=result["category"],
            raw=result,
        )

    def request_approval(
        self,
        *,
        requested_tool: str,
        risk_level: str,
        summary: str,
        payload_redacted: JsonObject,
        agent_id: str,
        session_id: str,
        expires_in_seconds: int,
        suggested_scopes: list[str] | None = None,
        action_id: str | None = None,
        node_id: str | None = None,
        risk_category: str | None = None,
        risk_family: str = "external_effect",
        resource_scope: str | None = None,
    ) -> JsonObject:
        return self._request(
            "POST",
            "/runtime/approvals",
            {
                "requested_tool": requested_tool,
                "risk_level": risk_level,
                "summary": summary,
                "payload_redacted": payload_redacted,
                "agent_id": agent_id,
                "session_id": session_id,
                "expires_in_seconds": expires_in_seconds,
                "suggested_scopes": suggested_scopes or ["once"],
                "action_id": action_id,
                "node_id": node_id,
                "risk_category": risk_category,
                "risk_family": risk_family,
                "resource_scope": resource_scope,
            },
        )

    def approval(
        self,
        *,
        requested_tool: str,
        risk_level: str,
        summary: str,
        payload_redacted: JsonObject,
        agent_id: str,
        session_id: str,
        expires_in_seconds: int = 300,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> ApprovalDecision:
        approval = self.request_approval(
            requested_tool=requested_tool,
            risk_level=risk_level,
            summary=summary,
            payload_redacted=payload_redacted,
            agent_id=agent_id,
            session_id=session_id,
            expires_in_seconds=expires_in_seconds,
            **kwargs,
        )
        return self.wait_for_approval(
            approval["approval_id"],
            timeout_seconds=timeout_seconds or float(expires_in_seconds),
        )

    def approval_result(self, approval_id: str) -> ApprovalDecision:
        result = self._request("GET", f"/runtime/approvals/{approval_id}/result")
        latest = _latest_response(result)
        return ApprovalDecision(
            approval_id=result["approval_id"],
            state=result["state"],
            selected_scope=result.get("selected_scope"),
            decision_type=latest.get("decision_type") if latest else None,
            alternate_directive=latest.get("alternate_directive") if latest else None,
            user_message=latest.get("user_message") if latest else None,
            constraints=list(latest.get("constraints", [])) if latest else [],
            raw=result,
        )

    def wait_for_approval(
        self,
        approval_id: str,
        *,
        timeout_seconds: float = 300.0,
        poll_interval_seconds: float | None = None,
    ) -> ApprovalDecision:
        return self._wait(
            lambda: self.approval_result(approval_id),
            lambda result: result.state in {"approved", "denied", "expired", "cancelled"}
            or result.decision_type in {"modified", "needs_info", "propose_policy"},
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            description=f"approval {approval_id}",
        )

    def cancel_approval(self, approval_id: str) -> ApprovalDecision:
        self._request("POST", f"/runtime/approvals/{approval_id}/cancel", {})
        return self.approval_result(approval_id)

    def request_assistance(
        self,
        *,
        agent_id: str,
        session_id: str,
        reason: str,
        node_id: str | None = None,
        approval_id: str | None = None,
        context_redacted: JsonObject | None = None,
        timeout_seconds: float = 300.0,
    ) -> AssistanceResult:
        request = self._request(
            "POST",
            "/runtime/tua/requests",
            {
                "agent_id": agent_id,
                "session_id": session_id,
                "reason": reason,
                "node_id": node_id,
                "approval_id": approval_id,
                "context_redacted": context_redacted or {},
            },
        )
        return self.wait_for_assistance(
            request["request_id"],
            timeout_seconds=timeout_seconds,
        )

    def assistance_result(self, request_id: str) -> AssistanceResult:
        result = self._request("GET", f"/runtime/tua/requests/{request_id}/result")
        latest = result.get("latest_session")
        messages = list(latest.get("messages", [])) if isinstance(latest, dict) else []
        return AssistanceResult(
            request_id=result["request"]["request_id"],
            state=result["request"]["state"],
            return_summary=result.get("return_summary"),
            latest_session=latest,
            messages=messages,
            raw=result,
        )

    def wait_for_assistance(
        self,
        request_id: str,
        *,
        timeout_seconds: float = 300.0,
        poll_interval_seconds: float | None = None,
    ) -> AssistanceResult:
        return self._wait(
            lambda: self.assistance_result(request_id),
            lambda result: result.return_summary is not None
            or result.state in {"returned_to_agent", "closed", "cancelled"},
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            description=f"assistance request {request_id}",
        )

    def request_browser_assistance(
        self,
        *,
        agent_id: str,
        session_id: str,
        reason: str,
        node_id: str | None = None,
        approval_id: str | None = None,
        context_redacted: JsonObject | None = None,
        timeout_seconds: float = 300.0,
    ) -> BrowserAssistanceResult:
        session = self._request(
            "POST",
            "/runtime/browser-assistance/sessions",
            {
                "agent_id": agent_id,
                "session_id": session_id,
                "reason": reason,
                "node_id": node_id,
                "approval_id": approval_id,
                "context_redacted": context_redacted or {},
            },
        )
        return self.wait_for_browser_assistance(
            session["browser_session_id"],
            timeout_seconds=timeout_seconds,
        )

    def browser_assistance_result(self, session_id: str) -> BrowserAssistanceResult:
        result = self._request(
            "GET",
            f"/runtime/browser-assistance/sessions/{session_id}/result",
        )
        session = result["session"]
        return BrowserAssistanceResult(
            session_id=session["browser_session_id"],
            state=session["state"],
            return_summary=result.get("return_summary"),
            user_action_notes=list(session.get("user_action_notes", [])),
            raw=result,
        )

    def wait_for_browser_assistance(
        self,
        session_id: str,
        *,
        timeout_seconds: float = 300.0,
        poll_interval_seconds: float | None = None,
    ) -> BrowserAssistanceResult:
        return self._wait(
            lambda: self.browser_assistance_result(session_id),
            lambda result: result.return_summary is not None
            or result.state in {"returned_to_agent", "closed", "failed"},
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            description=f"browser assistance session {session_id}",
        )

    def request_voice(
        self,
        *,
        agent_id: str,
        session_id: str | None = None,
        node_id: str | None = None,
        context_redacted: JsonObject | None = None,
        timeout_seconds: float = 300.0,
    ) -> VoiceInteractionResult:
        session = self._request(
            "POST",
            "/runtime/voice/sessions",
            {
                "agent_id": agent_id,
                "session_id": session_id,
                "node_id": node_id,
                "mode": "text_fallback",
                "context_redacted": context_redacted or {},
            },
        )
        return self.wait_for_voice(
            session["voice_session_id"],
            timeout_seconds=timeout_seconds,
        )

    def voice_result(self, session_id: str) -> VoiceInteractionResult:
        result = self._request("GET", f"/runtime/voice/sessions/{session_id}/result")
        session = result["session"]
        return VoiceInteractionResult(
            session_id=session["voice_session_id"],
            state=session["state"],
            transcript=list(result.get("messages", [])),
            raw=result,
        )

    def wait_for_voice(
        self,
        session_id: str,
        *,
        timeout_seconds: float = 300.0,
        poll_interval_seconds: float | None = None,
    ) -> VoiceInteractionResult:
        return self._wait(
            lambda: self.voice_result(session_id),
            lambda result: result.state == "closed",
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            description=f"voice session {session_id}",
        )

    def fetch_operator_session(self, session_id: str) -> JsonObject | None:
        result = self._request("GET", "/operator-sessions")
        for session in result.get("operator_sessions", []):
            if session.get("session_id") == session_id:
                return session
        return None

    def _request(
        self,
        method: str,
        path: str,
        body: JsonObject | None = None,
    ) -> JsonObject:
        payload = _drop_none(body)
        if self.transport is not None:
            return self.transport(method, path, payload, self.config.timeout_seconds)

        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        url = f"{self._base_url}{path}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        last_error: Exception | None = None
        for attempt in range(self.config.retry_attempts):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.config.timeout_seconds,
                ) as response:
                    raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                raise RuntimeClientError(f"{method} {path} failed with {exc.code}: {raw}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt + 1 >= self.config.retry_attempts:
                    break
                time.sleep(self.config.retry_backoff_seconds * (attempt + 1))
        raise RuntimeClientError(f"{method} {path} failed: {last_error}") from last_error

    def _wait(
        self,
        producer: Callable[[], Any],
        done: Callable[[Any], bool],
        *,
        timeout_seconds: float,
        poll_interval_seconds: float | None,
        description: str,
    ) -> Any:
        deadline = time.monotonic() + timeout_seconds
        interval = poll_interval_seconds or self.config.poll_interval_seconds
        while True:
            result = producer()
            if done(result):
                return result
            if time.monotonic() >= deadline:
                raise RuntimeClientTimeout(f"timed out waiting for {description}")
            time.sleep(interval)


def _latest_response(result: JsonObject) -> JsonObject | None:
    responses = result.get("responses", [])
    if not responses:
        return None
    return responses[-1]


def _drop_none(value: JsonObject | None) -> JsonObject | None:
    if value is None:
        return None
    return {key: item for key, item in value.items() if item is not None}


def _assert_loopback_url(base_url: str) -> None:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeClientError("gateway base URL must be an HTTP URL")
    if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
        return
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 80)
    except socket.gaierror as exc:
        raise RuntimeClientError(f"cannot resolve gateway host {parsed.hostname}") from exc
    for address in addresses:
        host = address[4][0]
        if host not in {"127.0.0.1", "::1"}:
            raise RuntimeClientError(
                "HermesRuntimeClient defaults to loopback gateway URLs; "
                "pass allow_non_loopback=True only for explicit Tailscale/dev use"
            )
