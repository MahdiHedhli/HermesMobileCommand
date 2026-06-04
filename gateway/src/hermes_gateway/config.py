from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    node_id: str = "node_local"
    node_display_name: str = "Local Hermes"
    node_environment: str = "homelab"
    node_fingerprint: str = "local-dev-fingerprint"
    gateway_base_url: str = "http://127.0.0.1:8787/v1"
    gateway_version: str = "0.1.0"
    hermes_version: str | None = None
    database_path: str = ".hermes-mobile-gateway/gateway.sqlite3"
    pairing_ttl_seconds: int = 300
    allowed_hermes_callers: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            node_id=os.getenv("HERMES_NODE_ID", cls.node_id),
            node_display_name=os.getenv("HERMES_NODE_DISPLAY_NAME", cls.node_display_name),
            node_environment=os.getenv("HERMES_NODE_ENVIRONMENT", cls.node_environment),
            node_fingerprint=os.getenv("HERMES_NODE_FINGERPRINT", cls.node_fingerprint),
            gateway_base_url=os.getenv("HERMES_GATEWAY_BASE_URL", cls.gateway_base_url),
            gateway_version=os.getenv("HERMES_GATEWAY_VERSION", cls.gateway_version),
            hermes_version=os.getenv("HERMES_VERSION"),
            database_path=os.getenv("HERMES_GATEWAY_DB", cls.database_path),
            pairing_ttl_seconds=int(
                os.getenv("HERMES_PAIRING_TTL_SECONDS", str(cls.pairing_ttl_seconds))
            ),
            allowed_hermes_callers=_csv_env("HERMES_ALLOWED_HERMES_CALLERS")
            or _csv_env("HERMES_GATEWAY_ALLOWED_HERMES_CALLERS"),
        )

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)


def _csv_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    return tuple(part.strip() for part in value.split(",") if part.strip())
