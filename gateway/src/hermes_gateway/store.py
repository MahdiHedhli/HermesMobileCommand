from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .ids import new_id
from .security import content_hash, expires_in, hash_token, now_utc, parse_utc, utc_iso


class SQLiteStore:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def connect(self) -> sqlite3.Connection:
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    gateway_base_url TEXT NOT NULL,
                    node_fingerprint TEXT NOT NULL,
                    gateway_version TEXT NOT NULL,
                    hermes_version TEXT,
                    health TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT
                );

                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    pairing_id TEXT PRIMARY KEY,
                    pairing_token_hash TEXT NOT NULL,
                    challenge TEXT NOT NULL,
                    status TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_fingerprint TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    requested_permissions_json TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    device_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    app_instance_id TEXT NOT NULL,
                    app_version TEXT,
                    device_public_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    permissions_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    last_seen_at TEXT
                );

                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_hash TEXT PRIMARY KEY,
                    token_type TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(device_id) REFERENCES devices(device_id)
                );

                CREATE TABLE IF NOT EXISTS request_nonces (
                    device_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (device_id, nonce),
                    FOREIGN KEY(device_id) REFERENCES devices(device_id)
                );

                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    agent_kind TEXT,
                    status TEXT NOT NULL,
                    active_session_id TEXT,
                    current_tool TEXT,
                    current_target TEXT,
                    tags_json TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    last_seen_at TEXT,
                    PRIMARY KEY (node_id, agent_id)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    conversation_id TEXT,
                    status TEXT NOT NULL,
                    title TEXT,
                    summary TEXT,
                    current_plan TEXT,
                    current_tool TEXT,
                    current_target TEXT,
                    started_at TEXT NOT NULL,
                    updated_at TEXT,
                    ended_at TEXT,
                    PRIMARY KEY (node_id, session_id)
                );

                CREATE TABLE IF NOT EXISTS approval_requests (
                    approval_id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    requested_tool TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_category TEXT,
                    summary TEXT NOT NULL,
                    full_payload_redacted_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    resource_scope TEXT,
                    state TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    action_id TEXT,
                    category TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    title_safe TEXT NOT NULL,
                    body_safe TEXT NOT NULL,
                    dedupe_key TEXT,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_attempt_at TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    agent_id TEXT,
                    session_id TEXT,
                    approval_id TEXT,
                    notification_id TEXT,
                    voice_session_id TEXT,
                    request_id TEXT NOT NULL,
                    previous_hash TEXT,
                    hash TEXT NOT NULL,
                    payload_redacted_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS event_envelopes (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    cursor TEXT,
                    node_id TEXT NOT NULL,
                    agent_id TEXT,
                    session_id TEXT,
                    conversation_id TEXT,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def upsert_node(self, node: dict[str, Any]) -> dict[str, Any]:
        created_at = node.get("created_at") or utc_iso()
        last_seen_at = node.get("last_seen_at") or created_at
        capabilities = node.get("capabilities") or [
            {"name": "events_websocket", "status": "available"},
            {"name": "pairing", "status": "available"},
            {"name": "mobile_notify", "status": "available"},
            {"name": "approvals", "status": "available"},
        ]
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO nodes (
                    node_id, display_name, environment, gateway_base_url, node_fingerprint,
                    gateway_version, hermes_version, health, tags_json, capabilities_json,
                    created_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    environment=excluded.environment,
                    gateway_base_url=excluded.gateway_base_url,
                    node_fingerprint=excluded.node_fingerprint,
                    gateway_version=excluded.gateway_version,
                    hermes_version=excluded.hermes_version,
                    health=excluded.health,
                    tags_json=excluded.tags_json,
                    capabilities_json=excluded.capabilities_json,
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    node["node_id"],
                    node["display_name"],
                    node["environment"],
                    node["gateway_base_url"],
                    node["node_fingerprint"],
                    node["gateway_version"],
                    node.get("hermes_version"),
                    node.get("health", "online"),
                    json.dumps(node.get("tags", [])),
                    json.dumps(capabilities),
                    created_at,
                    last_seen_at,
                ),
            )
        return self.get_node(node["node_id"])

    def get_node(self, node_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            raise KeyError(node_id)
        node = dict(row)
        node["tags"] = json.loads(node.pop("tags_json"))
        node["capabilities"] = json.loads(node.pop("capabilities_json"))
        node["agents"] = self.list_agents(node_id=node_id)
        return node

    def list_nodes(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT node_id FROM nodes ORDER BY display_name").fetchall()
        return [self.get_node(row["node_id"]) for row in rows]

    def upsert_agent(self, agent: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO agents (
                    agent_id, node_id, display_name, agent_kind, status, active_session_id,
                    current_tool, current_target, tags_json, capabilities_json, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id, agent_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    agent_kind=excluded.agent_kind,
                    status=excluded.status,
                    active_session_id=excluded.active_session_id,
                    current_tool=excluded.current_tool,
                    current_target=excluded.current_target,
                    tags_json=excluded.tags_json,
                    capabilities_json=excluded.capabilities_json,
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    agent["agent_id"],
                    agent["node_id"],
                    agent["display_name"],
                    agent.get("agent_kind"),
                    agent.get("status", "idle"),
                    agent.get("active_session_id"),
                    agent.get("current_tool"),
                    agent.get("current_target"),
                    json.dumps(agent.get("tags", [])),
                    json.dumps(agent.get("capabilities", [])),
                    agent.get("last_seen_at") or utc_iso(),
                ),
            )
        return self.get_agent(agent["node_id"], agent["agent_id"])

    def get_agent(self, node_id: str, agent_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM agents WHERE node_id = ? AND agent_id = ?", (node_id, agent_id)
            ).fetchone()
        if row is None:
            raise KeyError(agent_id)
        agent = dict(row)
        agent["tags"] = json.loads(agent.pop("tags_json"))
        agent["capabilities"] = json.loads(agent.pop("capabilities_json"))
        return agent

    def list_agents(self, node_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM agents"
        args: tuple[Any, ...] = ()
        if node_id:
            sql += " WHERE node_id = ?"
            args = (node_id,)
        sql += " ORDER BY display_name"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        agents = []
        for row in rows:
            agent = dict(row)
            agent["tags"] = json.loads(agent.pop("tags_json"))
            agent["capabilities"] = json.loads(agent.pop("capabilities_json"))
            agents.append(agent)
        return agents

    def upsert_session(self, session: dict[str, Any]) -> dict[str, Any]:
        now = utc_iso()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO sessions (
                    session_id, node_id, agent_id, conversation_id, status, title, summary,
                    current_plan, current_tool, current_target, started_at, updated_at, ended_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id, session_id) DO UPDATE SET
                    agent_id=excluded.agent_id,
                    conversation_id=excluded.conversation_id,
                    status=excluded.status,
                    title=excluded.title,
                    summary=excluded.summary,
                    current_plan=excluded.current_plan,
                    current_tool=excluded.current_tool,
                    current_target=excluded.current_target,
                    updated_at=excluded.updated_at,
                    ended_at=excluded.ended_at
                """,
                (
                    session["session_id"],
                    session["node_id"],
                    session["agent_id"],
                    session.get("conversation_id"),
                    session.get("status", "active"),
                    session.get("title"),
                    session.get("summary"),
                    session.get("current_plan"),
                    session.get("current_tool"),
                    session.get("current_target"),
                    session.get("started_at") or now,
                    session.get("updated_at") or now,
                    session.get("ended_at"),
                ),
            )
        return self.get_session(session["node_id"], session["session_id"])

    def get_session(self, node_id: str, session_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE node_id = ? AND session_id = ?",
                (node_id, session_id),
            ).fetchone()
        if row is None:
            raise KeyError(session_id)
        return dict(row)

    def list_sessions(
        self, node_id: str | None = None, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        where = []
        args: list[Any] = []
        if node_id:
            where.append("node_id = ?")
            args.append(node_id)
        if agent_id:
            where.append("agent_id = ?")
            args.append(agent_id)
        sql = "SELECT * FROM sessions"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC"
        with self.connect() as db:
            rows = db.execute(sql, tuple(args)).fetchall()
        return [dict(row) for row in rows]

    def create_pairing_session(
        self,
        *,
        node_id: str,
        node_fingerprint: str,
        display_name: str,
        requested_permissions: list[str],
        pairing_token: str,
        challenge: str,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        pairing_id = new_id("pair")
        expires_at = utc_iso(expires_in(ttl_seconds))
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO pairing_sessions (
                    pairing_id, pairing_token_hash, challenge, status, node_id,
                    node_fingerprint, display_name, requested_permissions_json,
                    expires_at, created_at
                )
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
                """,
                (
                    pairing_id,
                    hash_token(pairing_token),
                    challenge,
                    node_id,
                    node_fingerprint,
                    display_name,
                    json.dumps(requested_permissions),
                    expires_at,
                    utc_iso(),
                ),
            )
        return self.get_pairing_session(pairing_id, include_token=False) | {
            "pairing_token": pairing_token
        }

    def get_pairing_session(
        self, pairing_id: str, *, include_token: bool = False
    ) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM pairing_sessions WHERE pairing_id = ?", (pairing_id,)
            ).fetchone()
        if row is None:
            raise KeyError(pairing_id)
        pairing = dict(row)
        pairing["requested_permissions"] = json.loads(pairing.pop("requested_permissions_json"))
        if not include_token:
            pairing.pop("pairing_token_hash", None)
        return pairing

    def set_pairing_status(self, pairing_id: str, status: str) -> None:
        completed_at = utc_iso() if status == "completed" else None
        with self.connect() as db:
            db.execute(
                "UPDATE pairing_sessions SET status = ?, completed_at = ? WHERE pairing_id = ?",
                (status, completed_at, pairing_id),
            )

    def create_device(
        self,
        *,
        node_id: str,
        device_name: str,
        platform: str,
        app_instance_id: str,
        app_version: str | None,
        device_public_key: str,
        permissions: list[str],
    ) -> dict[str, Any]:
        device_id = new_id("dev")
        registered_at = utc_iso()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO devices (
                    device_id, user_id, node_id, device_name, platform, app_instance_id,
                    app_version, device_public_key, status, permissions_json,
                    registered_at, last_seen_at
                )
                VALUES (?, 'owner', ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    device_id,
                    node_id,
                    device_name,
                    platform,
                    app_instance_id,
                    app_version,
                    device_public_key,
                    json.dumps(permissions),
                    registered_at,
                    registered_at,
                ),
            )
        return self.get_device(device_id)

    def get_device(self, device_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if row is None:
            raise KeyError(device_id)
        device = dict(row)
        device["permissions"] = json.loads(device.pop("permissions_json"))
        return device

    def list_devices(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM devices ORDER BY registered_at DESC").fetchall()
        devices = []
        for row in rows:
            device = dict(row)
            device["permissions"] = json.loads(device.pop("permissions_json"))
            devices.append(device)
        return devices

    def revoke_device(self, device_id: str) -> bool:
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE devices SET status = 'revoked' WHERE device_id = ?", (device_id,)
            )
            db.execute(
                "UPDATE auth_tokens SET revoked_at = ? WHERE device_id = ?",
                (utc_iso(), device_id),
            )
        return cursor.rowcount > 0

    def create_auth_token(
        self, *, token: str, token_type: str, device_id: str, ttl_seconds: int
    ) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO auth_tokens (token_hash, token_type, device_id, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hash_token(token),
                    token_type,
                    device_id,
                    utc_iso(expires_in(ttl_seconds)),
                    utc_iso(),
                ),
            )

    def verify_access_token(self, token: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT d.*
                FROM auth_tokens t
                JOIN devices d ON d.device_id = t.device_id
                WHERE t.token_hash = ?
                  AND t.token_type = 'access'
                  AND t.revoked_at IS NULL
                  AND d.status = 'active'
                """,
                (hash_token(token),),
            ).fetchone()
        if row is None:
            return None
        token_row = self._get_token(token)
        if token_row is None or parse_utc(token_row["expires_at"]) <= now_utc():
            return None
        device = dict(row)
        device["permissions"] = json.loads(device.pop("permissions_json"))
        return device

    def verify_refresh_token(self, token: str) -> dict[str, Any] | None:
        token_row = self._get_token(token)
        if token_row is None or token_row["token_type"] != "refresh":
            return None
        if token_row["revoked_at"] or parse_utc(token_row["expires_at"]) <= now_utc():
            return None
        device = self.get_device(token_row["device_id"])
        if device["status"] != "active":
            return None
        return device

    def _get_token(self, token: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM auth_tokens WHERE token_hash = ?", (hash_token(token),)
            ).fetchone()
        return dict(row) if row else None

    def record_request_nonce(self, *, device_id: str, nonce: str, timestamp: int) -> bool:
        try:
            with self.connect() as db:
                db.execute(
                    """
                    INSERT INTO request_nonces (device_id, nonce, timestamp, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (device_id, nonce, timestamp, utc_iso()),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def create_approval(self, approval: dict[str, Any]) -> dict[str, Any]:
        payload = approval.get("full_payload_redacted", {})
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO approval_requests (
                    approval_id, action_id, node_id, agent_id, session_id, requested_tool,
                    risk_level, risk_category, summary, full_payload_redacted_json,
                    payload_hash, resource_scope, state, options_json, requested_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval["approval_id"],
                    approval["action_id"],
                    approval["node_id"],
                    approval["agent_id"],
                    approval["session_id"],
                    approval["requested_tool"],
                    approval["risk_level"],
                    approval.get("risk_category"),
                    approval["summary"],
                    json.dumps(payload),
                    approval.get("payload_hash") or content_hash(payload),
                    approval.get("resource_scope"),
                    approval.get("state", "pending"),
                    json.dumps(approval.get("options", [])),
                    approval.get("requested_at") or utc_iso(),
                    approval["expires_at"],
                ),
            )
        return self.get_approval(approval["approval_id"])

    def get_approval(self, approval_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM approval_requests WHERE approval_id = ?", (approval_id,)
            ).fetchone()
        if row is None:
            raise KeyError(approval_id)
        return self._approval_from_row(row)

    def list_approvals(self, state: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM approval_requests"
        args: tuple[Any, ...] = ()
        if state:
            sql += " WHERE state = ?"
            args = (state,)
        sql += " ORDER BY requested_at DESC"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def resolve_approval(self, approval_id: str, state: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE approval_requests SET state = ? WHERE approval_id = ?",
                (state, approval_id),
            )

    def _approval_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        approval = dict(row)
        approval["full_payload_redacted"] = json.loads(
            approval.pop("full_payload_redacted_json")
        )
        approval["options"] = json.loads(approval.pop("options_json"))
        approval.pop("payload_hash", None)
        approval.pop("requested_at", None)
        return approval

    def create_notification(self, notification: dict[str, Any]) -> dict[str, Any]:
        notification_id = notification.get("notification_id") or new_id("ntf")
        created_at = notification.get("created_at") or utc_iso()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO notifications (
                    notification_id, node_id, agent_id, session_id, action_id, category,
                    urgency, title_safe, body_safe, dedupe_key, state, created_at,
                    last_attempt_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    notification["node_id"],
                    notification["agent_id"],
                    notification["session_id"],
                    notification.get("action_id"),
                    notification["category"],
                    notification["urgency"],
                    notification["title_safe"],
                    notification["body_safe"],
                    notification.get("dedupe_key"),
                    notification.get("state", "queued"),
                    created_at,
                    notification.get("last_attempt_at"),
                ),
            )
        return self.get_notification(notification_id)

    def get_notification(self, notification_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM notifications WHERE notification_id = ?", (notification_id,)
            ).fetchone()
        if row is None:
            raise KeyError(notification_id)
        return dict(row)

    def list_notifications(self, category: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM notifications"
        args: tuple[Any, ...] = ()
        if category:
            sql += " WHERE category = ?"
            args = (category,)
        sql += " ORDER BY created_at DESC"
        with self.connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [dict(row) for row in rows]

    def append_audit_event(
        self,
        *,
        event_type: str,
        actor_type: str,
        actor_id: str,
        node_id: str,
        request_id: str,
        payload_redacted: dict[str, Any] | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        approval_id: str | None = None,
        notification_id: str | None = None,
        voice_session_id: str | None = None,
    ) -> dict[str, Any]:
        created_at = utc_iso()
        previous_hash = self.latest_audit_hash()
        audit_event_id = new_id("aud")
        event_hash = content_hash(
            {
                "audit_event_id": audit_event_id,
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "node_id": node_id,
                "request_id": request_id,
                "previous_hash": previous_hash,
                "payload_redacted": payload_redacted or {},
                "created_at": created_at,
            }
        )
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO audit_events (
                    audit_event_id, event_type, actor_type, actor_id, node_id, agent_id,
                    session_id, approval_id, notification_id, voice_session_id, request_id,
                    previous_hash, hash, payload_redacted_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_event_id,
                    event_type,
                    actor_type,
                    actor_id,
                    node_id,
                    agent_id,
                    session_id,
                    approval_id,
                    notification_id,
                    voice_session_id,
                    request_id,
                    previous_hash,
                    event_hash,
                    json.dumps(payload_redacted or {}),
                    created_at,
                ),
            )
        return self.get_audit_event(audit_event_id)

    def latest_audit_hash(self) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return row["hash"] if row else None

    def get_audit_event(self, audit_event_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM audit_events WHERE audit_event_id = ?", (audit_event_id,)
            ).fetchone()
        if row is None:
            raise KeyError(audit_event_id)
        return self._audit_from_row(row)

    def list_audit_events(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM audit_events"
        args: list[Any] = []
        if event_type:
            sql += " WHERE event_type = ?"
            args.append(event_type)
        sql += " ORDER BY sequence DESC LIMIT ?"
        args.append(limit)
        with self.connect() as db:
            rows = db.execute(sql, tuple(args)).fetchall()
        return [self._audit_from_row(row) for row in rows]

    def _audit_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        audit = dict(row)
        audit.pop("sequence", None)
        audit["payload_redacted"] = json.loads(audit.pop("payload_redacted_json") or "{}")
        return audit

    def create_event(
        self,
        *,
        node_id: str,
        event_type: str,
        payload: dict[str, Any],
        severity: str = "info",
        agent_id: str | None = None,
        session_id: str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = new_id("evt")
        occurred_at = utc_iso()
        with self.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO event_envelopes (
                    event_id, node_id, agent_id, session_id, conversation_id, type,
                    severity, occurred_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    node_id,
                    agent_id,
                    session_id,
                    conversation_id,
                    event_type,
                    severity,
                    occurred_at,
                    json.dumps(payload),
                ),
            )
            sequence = cursor.lastrowid
            event_cursor = f"{node_id}:{sequence:012d}"
            db.execute(
                "UPDATE event_envelopes SET cursor = ? WHERE sequence = ?",
                (event_cursor, sequence),
            )
        return self.get_event_by_id(event_id)

    def get_event_by_id(self, event_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM event_envelopes WHERE event_id = ?", (event_id,)
            ).fetchone()
        if row is None:
            raise KeyError(event_id)
        return self._event_from_row(row)

    def list_events_after(self, after: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        sequence = self._cursor_sequence(after)
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT * FROM event_envelopes
                WHERE sequence > ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (sequence, limit),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def event_count(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS count FROM event_envelopes").fetchone()
        return int(row["count"])

    def _event_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        event = dict(row)
        event.pop("sequence", None)
        event["payload"] = json.loads(event.pop("payload_json"))
        return event

    def _cursor_sequence(self, cursor: str | None) -> int:
        if not cursor:
            return 0
        try:
            return int(cursor.rsplit(":", 1)[1])
        except (IndexError, ValueError):
            return 0

    def seed_mock_data(self, *, node_id: str) -> None:
        if self.list_agents(node_id=node_id):
            return
        agent_id = "agent_mock"
        session_id = "sess_mock"
        self.upsert_agent(
            {
                "agent_id": agent_id,
                "node_id": node_id,
                "display_name": "Mock Hermes Agent",
                "agent_kind": "primary",
                "status": "idle",
                "capabilities": [
                    {"name": "chat", "status": "available"},
                    {"name": "approvals", "status": "available"},
                ],
            }
        )
        self.upsert_session(
            {
                "session_id": session_id,
                "node_id": node_id,
                "agent_id": agent_id,
                "status": "active",
                "title": "Mock control-plane session",
                "summary": "Seed session for gateway smoke tests.",
                "current_plan": "Waiting for mobile control-plane events.",
            }
        )
        if self.event_count() == 0:
            for event_type, payload in self.mock_events(agent_id=agent_id, session_id=session_id):
                self.create_event(
                    node_id=node_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    event_type=event_type,
                    payload=payload,
                )

    def mock_events(
        self, *, agent_id: str, session_id: str
    ) -> Iterable[tuple[str, dict[str, Any]]]:
        return (
            ("agent.status", {"agent_id": agent_id, "status": "idle"}),
            ("agent.activity", {"session_id": session_id, "summary": "Mock activity event"}),
            ("approval.requested", {"approval_id": "approval_mock", "risk_level": "medium"}),
            ("approval.resolved", {"approval_id": "approval_mock", "state": "denied"}),
            ("notification.created", {"notification_id": "notification_mock"}),
            ("system.health", {"status": "healthy"}),
        )
