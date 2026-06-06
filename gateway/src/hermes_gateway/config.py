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
    cors_allowed_origin_regex: str | None = r"^http://(localhost|127\.0\.0\.1):[0-9]+$"
    tui_enable_local_pty: bool = False
    tui_allowed_commands: tuple[str, ...] = ("/bin/sh",)
    tui_default_command: str = "/bin/sh"
    tui_allowed_working_directory: str = "."
    tui_max_sessions: int = 2
    tui_idle_timeout_seconds: int = 900
    tui_attach_token_ttl_seconds: int = 60
    tui_output_retention_enabled: bool = False

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
            cors_allowed_origin_regex=os.getenv(
                "HERMES_GATEWAY_CORS_ALLOWED_ORIGIN_REGEX",
                cls.cors_allowed_origin_regex or "",
            )
            or None,
            tui_enable_local_pty=_bool_env(
                "HERMES_TUI_ENABLE_LOCAL_PTY", cls.tui_enable_local_pty
            ),
            tui_allowed_commands=_csv_env("HERMES_TUI_ALLOWED_COMMANDS")
            or cls.tui_allowed_commands,
            tui_default_command=os.getenv(
                "HERMES_TUI_DEFAULT_COMMAND", cls.tui_default_command
            ),
            tui_allowed_working_directory=os.getenv(
                "HERMES_TUI_ALLOWED_WORKING_DIRECTORY",
                cls.tui_allowed_working_directory,
            ),
            tui_max_sessions=int(os.getenv("HERMES_TUI_MAX_SESSIONS", str(cls.tui_max_sessions))),
            tui_idle_timeout_seconds=int(
                os.getenv(
                    "HERMES_TUI_IDLE_TIMEOUT_SECONDS",
                    str(cls.tui_idle_timeout_seconds),
                )
            ),
            tui_attach_token_ttl_seconds=int(
                os.getenv(
                    "HERMES_TUI_ATTACH_TOKEN_TTL_SECONDS",
                    str(cls.tui_attach_token_ttl_seconds),
                )
            ),
            tui_output_retention_enabled=_bool_env(
                "HERMES_TUI_OUTPUT_RETENTION_ENABLED",
                cls.tui_output_retention_enabled,
            ),
        )

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)


def _csv_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
