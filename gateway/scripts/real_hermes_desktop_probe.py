from __future__ import annotations

import http.client
import json
import plistlib
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_APP = Path("/Applications/Hermes.app")
HERMES_HOME = HOME / ".hermes"
HERMES_RUNTIME = HERMES_HOME / "hermes-agent"
HERMES_VENV = HERMES_RUNTIME / "venv"
HERMES_DESKTOP_SUPPORT = HOME / "Library" / "Application Support" / "Hermes"
HERMES_PLIST = HOME / "Library" / "Preferences" / "com.nousresearch.hermes.plist"
HERMES_CONFIG = HERMES_HOME / "config.yaml"
HERMES_ENV = HERMES_HOME / ".env"
HERMES_STATE_DB = HERMES_HOME / "state.db"
HERMES_LOGS = HERMES_HOME / "logs"


def main() -> int:
    result = {
        "probe": {
            "name": "real_hermes_desktop_probe",
            "timestamp": datetime.now(UTC).isoformat(),
            "non_destructive": True,
            "secrets_read": False,
        },
        "installation": _installation(),
        "runtime": _runtime(),
        "desktop_backend": _desktop_backend(),
        "state": _state_db_summary(),
        "logs": _logs_summary(),
        "processes": _process_summary(),
        "integration_candidates": _integration_candidates(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _installation() -> dict[str, Any]:
    info = _read_plist(HERMES_APP / "Contents" / "Info.plist")
    return {
        "app": _path_info(HERMES_APP),
        "bundle_identifier": info.get("CFBundleIdentifier"),
        "display_name": info.get("CFBundleDisplayName") or info.get("CFBundleName"),
        "version": info.get("CFBundleShortVersionString"),
        "build": info.get("CFBundleVersion"),
        "electron_entry": _path_info(HERMES_APP / "Contents" / "Resources" / "app.asar"),
        "desktop_support": _path_info(HERMES_DESKTOP_SUPPORT),
        "preferences_plist": _path_info(HERMES_PLIST),
    }


def _runtime() -> dict[str, Any]:
    return {
        "hermes_home": _path_info(HERMES_HOME),
        "runtime_root": _path_info(HERMES_RUNTIME),
        "venv": _path_info(HERMES_VENV),
        "cli_shim": _path_info(HOME / ".local" / "bin" / "hermes"),
        "venv_cli": _path_info(HERMES_VENV / "bin" / "hermes"),
        "venv_agent_cli": _path_info(HERMES_VENV / "bin" / "hermes-agent"),
        "venv_acp_cli": _path_info(HERMES_VENV / "bin" / "hermes-acp"),
        "config": {
            **_path_info(HERMES_CONFIG),
            "redacted_shape": _redacted_config_shape(),
        },
        "env": {
            **_path_info(HERMES_ENV),
            "redacted": True,
        },
        "state_db": _path_info(HERMES_STATE_DB),
    }


def _desktop_backend() -> dict[str, Any]:
    active: dict[str, Any] | None = None
    for port in range(9120, 9200):
        status = _http_json("127.0.0.1", port, "/api/status")
        if status.get("ok"):
            sessions_auth = _http_status("127.0.0.1", port, "/api/sessions")
            active = {
                "host": "127.0.0.1",
                "port": port,
                "status": status["json"],
                "sessions_without_token_status": sessions_auth.get("status"),
            }
            break
    return {
        "active_dashboard": active,
        "expected_port_range": "9120-9199",
        "public_status_endpoint": "/api/status",
        "protected_endpoint_probe": "/api/sessions",
    }


def _state_db_summary() -> dict[str, Any]:
    if not HERMES_STATE_DB.exists():
        return {"exists": False}
    try:
        with sqlite3.connect(str(HERMES_STATE_DB)) as conn:
            conn.row_factory = sqlite3.Row
            tables = [
                row["name"]
                for row in conn.execute(
                    "select name from sqlite_master where type='table' order by name"
                )
            ]
            sessions = [
                dict(row)
                for row in conn.execute(
                    """
                    select id, source, datetime(started_at, 'unixepoch') as started_at,
                           ended_at is null as active, message_count, tool_call_count
                    from sessions
                    order by started_at desc
                    limit 8
                    """
                )
            ]
    except sqlite3.Error as exc:
        return {"exists": True, "error": str(exc)}
    return {"exists": True, "tables": tables, "recent_sessions": sessions}


def _logs_summary() -> list[dict[str, Any]]:
    if not HERMES_LOGS.exists():
        return []
    summaries = []
    for path in sorted(HERMES_LOGS.glob("*.log")):
        try:
            stat = path.stat()
        except OSError:
            continue
        summaries.append(
            {
                "path": str(path),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            }
        )
    return summaries


def _process_summary() -> list[dict[str, Any]]:
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    processes = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "Hermes.app" not in stripped and "hermes_cli.main" not in stripped:
            continue
        pid, _, command = stripped.partition(" ")
        processes.append({"pid": pid, "command": command})
    return processes


def _integration_candidates() -> dict[str, list[str]]:
    root = str(HERMES_RUNTIME)
    return {
        "approval": [
            f"{root}/tools/approval.py",
            f"{root}/acp_adapter/permissions.py",
            f"{root}/gateway/platforms/api_server.py",
            f"{root}/gateway/run.py",
        ],
        "assistance": [
            f"{root}/tools/clarify_gateway.py",
            f"{root}/apps/shared/src/json-rpc-gateway.ts",
            f"{root}/ui-tui/src/gatewayTypes.ts",
        ],
        "notifications": [
            "/Applications/Hermes.app/Contents/Resources/app.asar electron/main.cjs hermes:notify",
            f"{root}/tools/terminal_tool.py",
            f"{root}/gateway/run.py",
            f"{root}/gateway/stream_consumer.py",
        ],
        "desktop_api": [
            "http://127.0.0.1:9120-9199/api/status",
            "ws://127.0.0.1:9120-9199/api/ws?token=REDACTED_DESKTOP_TOKEN",
            "ws://127.0.0.1:9120-9199/api/pty?ticket=REDACTED_PTY_TICKET",
            "ws://127.0.0.1:9120-9199/api/events?channel=CHANNEL_ID",
        ],
    }


def _read_plist(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            value = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return {}
    return value if isinstance(value, dict) else {}


def _redacted_config_shape() -> dict[str, Any] | None:
    if not HERMES_CONFIG.exists():
        return None
    try:
        import yaml
    except ImportError:
        return {"error": "pyyaml unavailable"}
    try:
        with HERMES_CONFIG.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        return {"error": str(exc)}
    if not isinstance(data, dict):
        return {"type": type(data).__name__}
    interesting = {}
    for section in (
        "approvals",
        "gateway",
        "display",
        "voice",
        "tts",
        "stt",
        "hooks",
        "hooks_auto_accept",
        "browser",
        "tools",
        "auxiliary",
    ):
        if section not in data:
            continue
        value = data[section]
        if isinstance(value, dict):
            interesting[section] = sorted(str(key) for key in value.keys())
        else:
            interesting[section] = type(value).__name__
    return interesting


def _http_json(host: str, port: int, path: str) -> dict[str, Any]:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=0.35)
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read(1_000_000)
        conn.close()
    except (OSError, http.client.HTTPException, TimeoutError):
        return {"ok": False}
    if response.status < 200 or response.status >= 300:
        return {"ok": False, "status": response.status}
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "status": response.status}
    return {"ok": True, "status": response.status, "json": parsed}


def _http_status(host: str, port: int, path: str) -> dict[str, Any]:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=0.35)
        conn.request("GET", path)
        response = conn.getresponse()
        response.read()
        conn.close()
        return {"status": response.status}
    except (OSError, http.client.HTTPException, TimeoutError):
        return {"status": None}


def _path_info(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "exists": False}
    return {
        "path": str(path),
        "exists": True,
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
        "size_bytes": stat.st_size if path.is_file() else None,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


if __name__ == "__main__":
    raise SystemExit(main())
