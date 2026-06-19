"""APNs push dispatch (token-based / .p8 auth key).

Sends a wake-up hint to the operator's phone when a clearance needs attention.
Push payloads are HINTS ONLY — no secrets, no raw aircraft text (ADR-0005); the
durable clearance state lives in the gateway + audit log. Best-effort and
non-blocking: failures are logged, never raised, and the approval flow does not
wait on delivery.

Configuration comes from Settings (APNS_KEY_PATH / APNS_KEY_ID / APNS_TEAM_ID /
APNS_TOPIC / APNS_ENVIRONMENT). When unconfigured, ``configured`` is False and
dispatch is a no-op so the gateway runs exactly as before.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from .config import Settings

logger = logging.getLogger(__name__)

_PROD_HOST = "https://api.push.apple.com"
_SANDBOX_HOST = "https://api.sandbox.push.apple.com"
# APNs allows reusing a provider token for 20–60 min; refresh well within that.
_TOKEN_TTL_SECONDS = 45 * 60


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class ApnsPushDispatcher:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._jwt: str | None = None
        self._jwt_iat: float = 0.0
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return self._settings.push_configured

    @property
    def _host(self) -> str:
        return _SANDBOX_HOST if self._settings.apns_environment == "sandbox" else _PROD_HOST

    def _provider_token(self) -> str:
        """Build (and cache) the ES256 provider JWT signed with the .p8 key."""
        now = time.time()
        with self._lock:
            if self._jwt and (now - self._jwt_iat) < _TOKEN_TTL_SECONDS:
                return self._jwt
            with open(self._settings.apns_key_path, "rb") as handle:  # type: ignore[arg-type]
                private_key = serialization.load_pem_private_key(handle.read(), password=None)
            header = {"alg": "ES256", "kid": self._settings.apns_key_id}
            claims = {"iss": self._settings.apns_team_id, "iat": int(now)}
            signing_input = (
                _b64url(json.dumps(header, separators=(",", ":")).encode())
                + "."
                + _b64url(json.dumps(claims, separators=(",", ":")).encode())
            ).encode("ascii")
            der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
            r, s = decode_dss_signature(der)
            raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
            self._jwt = signing_input.decode("ascii") + "." + _b64url(raw_sig)
            self._jwt_iat = now
            return self._jwt

    @staticmethod
    def build_payload(
        *, title: str, body: str, approval_id: str, short_code: str
    ) -> dict[str, Any]:
        """Hint-only payload — no secrets, no raw aircraft text (ADR-0005)."""
        return {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
                "interruption-level": "time-sensitive",
            },
            "approval_id": approval_id,
            "short_code": short_code,
            "category": "clearance",
        }

    def dispatch_clearance(
        self,
        device_tokens: list[str],
        *,
        title: str,
        body: str,
        approval_id: str,
        short_code: str,
    ) -> None:
        """Fire-and-forget: send a clearance hint to each device token."""
        if not self.configured or not device_tokens:
            return
        payload = self.build_payload(
            title=title, body=body, approval_id=approval_id, short_code=short_code
        )
        thread = threading.Thread(
            target=self._send_all,
            args=(list(device_tokens), payload),
            daemon=True,
        )
        thread.start()

    def _send_all(self, device_tokens: list[str], payload: dict[str, Any]) -> None:
        try:
            import httpx  # lazy — keeps the gateway importable without http2 extras
        except ImportError:
            logger.warning("apns: httpx not installed; push skipped")
            return
        try:
            token = self._provider_token()
        except Exception as exc:  # bad/missing key — log, never raise
            logger.warning("apns: could not build provider token: %s", exc)
            return
        body = json.dumps(payload).encode("utf-8")
        try:
            with httpx.Client(http2=True, timeout=10.0) as client:
                for device_token in device_tokens:
                    self._send_one(client, token, device_token, body, payload["aps"])
        except Exception as exc:  # network/http2 issues — best effort
            logger.warning("apns: dispatch failed: %s", exc)

    def _send_one(self, client: Any, jwt: str, device_token: str, body: bytes, _aps: Any) -> None:
        try:
            resp = client.post(
                f"{self._host}/3/device/{device_token}",
                content=body,
                headers={
                    "authorization": f"bearer {jwt}",
                    "apns-topic": self._settings.apns_topic,
                    "apns-push-type": "alert",
                    "apns-priority": "10",
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "apns: %s -> %s %s",
                    device_token[:8], resp.status_code, resp.text[:200],
                )
        except Exception as exc:
            logger.warning("apns: send to %s failed: %s", device_token[:8], exc)
