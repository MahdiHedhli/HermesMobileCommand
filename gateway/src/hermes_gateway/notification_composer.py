from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .schemas import MobileNotifyRequest
from .security import has_secret_text

MAX_RAW_TITLE_CHARS = 120
MAX_RAW_BODY_CHARS = 800
SAFE_OPERATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._/-]{0,63}$")
TOKEN_LIKE_RE = re.compile(
    r"(?i)(bearer\s+[a-z0-9._~+/-]{12,}|"
    r"(api[_-]?key|token|secret|password)\s*[:=]\s*[^,\s]{4,}|"
    r"(ghp|xoxb|sk)-[a-z0-9_-]{8,})"
)


@dataclass(frozen=True)
class ComposedNotification:
    title: str
    body: str
    mode: str
    template: str
    unsafe_input_detected: bool
    unsafe_reasons: list[str]
    safe_fields: dict[str, Any]


def compose_notification(payload: MobileNotifyRequest) -> ComposedNotification:
    reasons = _unsafe_reasons(payload)
    safe_fields = _safe_fields(payload)
    subject = safe_fields["subject_display_name"]
    risk = safe_fields["risk_family"]
    operation = safe_fields["operation_label"]

    if payload.category == "approval_required":
        title = "Clearance required"
        body = f"{subject} requests {risk} clearance for {operation}."
        template = "approval_required"
    elif payload.category == "security_alert":
        title = "Security alert"
        body = f"{subject} reported a security event."
        template = "security_alert"
    elif payload.category == "agent_blocked":
        title = "Backend blocked"
        body = f"{subject} is waiting for operator input."
        template = "agent_blocked"
    elif payload.category == "task_complete":
        title = "Work complete"
        body = f"{subject} completed a task."
        template = "task_complete"
    elif payload.category == "system_health":
        title = "System health"
        body = f"{subject} reported a health update."
        template = "system_health"
    elif payload.category == "voice_callback":
        title = "Voice callback"
        body = f"{subject} requests a voice callback."
        template = "voice_callback"
    else:
        title = "ACT notification"
        body = f"{subject} requests operator attention."
        template = "fallback"

    return ComposedNotification(
        title=title,
        body=body,
        mode="template_sanitized" if reasons else "template_allowlist",
        template=template,
        unsafe_input_detected=bool(reasons),
        unsafe_reasons=reasons,
        safe_fields=safe_fields,
    )


def _safe_fields(payload: MobileNotifyRequest) -> dict[str, Any]:
    subject = _safe_label(payload.subject_display_name) or _safe_label(payload.agent_id)
    return {
        "backend_display_name": _safe_label(payload.backend_display_name) or "ACT backend",
        "subject_display_name": subject or "Backend",
        "risk_family": _safe_label(payload.risk_family) or _risk_from_category(payload.category),
        "clearance_category": _safe_label(payload.clearance_category) or payload.category,
        "action_category": _safe_label(payload.action_category) or "operator action",
        "operation_label": _safe_label(payload.operation_label) or _operation_from_category(
            payload.category
        ),
        "urgency": payload.urgency,
        "pending_count": payload.pending_count,
    }


def _safe_label(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not SAFE_OPERATION_RE.fullmatch(cleaned):
        return None
    if has_secret_text(cleaned) or _looks_token_like(cleaned) or _high_entropy(cleaned):
        return None
    return cleaned


def _unsafe_reasons(payload: MobileNotifyRequest) -> list[str]:
    reasons: list[str] = []
    if len(payload.title) > MAX_RAW_TITLE_CHARS:
        reasons.append("raw_title_too_large")
    if len(payload.body) > MAX_RAW_BODY_CHARS:
        reasons.append("raw_body_too_large")
    raw_parts = [payload.title, payload.body]
    if has_secret_text(*raw_parts):
        reasons.append("secret_marker_detected")
    if any(_looks_token_like(part) for part in raw_parts):
        reasons.append("token_like_text_detected")
    if any(_high_entropy(part) for part in raw_parts):
        reasons.append("high_entropy_text_detected")
    return reasons


def _looks_token_like(value: str | None) -> bool:
    return bool(value and TOKEN_LIKE_RE.search(value))


def _high_entropy(value: str | None) -> bool:
    if not value:
        return False
    candidates = re.findall(r"[A-Za-z0-9+/=_-]{24,}", value)
    return any(_shannon_entropy(candidate) >= 4.2 for candidate in candidates)


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    total = len(value)
    return -sum((count / total) * math.log2(count / total) for count in _counts(value).values())


def _counts(value: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    return counts


def _risk_from_category(category: str) -> str:
    return {
        "approval_required": "consequential",
        "security_alert": "security",
        "agent_blocked": "routine",
        "task_complete": "routine",
        "system_health": "routine",
        "voice_callback": "routine",
    }.get(category, "routine")


def _operation_from_category(category: str) -> str:
    return {
        "approval_required": "a pending action",
        "security_alert": "a security review",
        "agent_blocked": "operator assistance",
        "task_complete": "completed work",
        "system_health": "a health update",
        "voice_callback": "voice assistance",
    }.get(category, "operator attention")
