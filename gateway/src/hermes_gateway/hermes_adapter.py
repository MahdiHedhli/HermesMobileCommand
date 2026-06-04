from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class HermesToolAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class HermesToolAdapter:
    gateway_base_url: str = "http://127.0.0.1:8787/v1"
    timeout_seconds: float = 5.0

    def mobile_notify(
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
    ) -> dict[str, Any]:
        return self._post(
            "/notifications/mobile_notify",
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

    def approval_requested(
        self,
        *,
        requested_tool: str,
        risk_level: str,
        summary: str,
        payload_redacted: dict[str, Any],
        agent_id: str,
        session_id: str,
        expires_in_seconds: int,
        suggested_scopes: list[str] | None = None,
        action_id: str | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "/hermes/tools/approval_requested",
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
            },
        )

    def approval_status(self, *, approval_id: str) -> dict[str, Any]:
        return self._post("/hermes/tools/approval_status", {"approval_id": approval_id})

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(_without_none(payload), separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.gateway_base_url.rstrip('/')}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise HermesToolAdapterError(
                f"gateway rejected Hermes tool call: {exc.code} {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise HermesToolAdapterError(f"gateway unavailable: {exc}") from exc


def _without_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}
