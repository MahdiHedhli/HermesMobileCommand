from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any


def now_utc() -> datetime:
    return datetime.now(UTC)


def utc_iso(value: datetime | None = None) -> str:
    return (value or now_utc()).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def expires_in(seconds: int) -> datetime:
    return now_utc() + timedelta(seconds=seconds)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def compare_token(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def has_secret_text(*parts: str | None) -> bool:
    markers = (
        "password=",
        "password:",
        "api_key",
        "apikey",
        "secret=",
        "secret:",
        "token=",
        "token:",
        "begin private key",
        "ssh-rsa ",
        "sk-",
        "ghp_",
        "xoxb-",
    )
    text = " ".join(part or "" for part in parts).lower()
    return any(marker in text for marker in markers)
