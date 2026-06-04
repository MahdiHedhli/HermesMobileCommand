from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Permission = Literal["read_state", "chat", "approve", "intervene", "manage_devices", "voice"]
Platform = Literal["ios", "android"]
DeviceStatus = Literal["active", "revoked", "lost", "rotating", "disabled"]
Environment = Literal["homelab", "laptop", "cloud", "workstation", "vps", "work_vm", "custom"]
AgentStatus = Literal[
    "idle", "running", "blocked", "paused", "stopping", "offline", "error", "quarantined"
]
SessionStatus = Literal["active", "blocked", "paused", "completed", "failed", "cancelled"]
ApprovalState = Literal["pending", "approved", "denied", "expired", "cancelled"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ApprovalScope = Literal["once", "session", "agent", "permanent"]
NotificationCategory = Literal[
    "approval_required",
    "security_alert",
    "agent_blocked",
    "task_complete",
    "system_health",
    "voice_callback",
]
NotificationUrgency = Literal["low", "normal", "high", "critical"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    error: str
    message: str | None = None
    request_id: str


class Capability(BaseModel):
    name: str
    status: Literal[
        "available",
        "disabled",
        "requires_pairing",
        "requires_permission",
        "unsupported",
        "degraded",
    ]


class GatewayHealth(BaseModel):
    node_id: str
    status: Literal["healthy", "degraded", "unhealthy"]
    gateway_version: str
    hermes_version: str | None = None
    checked_at: datetime
    services: dict[str, Literal["healthy", "degraded", "unhealthy", "unavailable"]] = Field(
        default_factory=dict
    )


class NodeRegistration(StrictModel):
    node_id: str | None = None
    display_name: str
    environment: Environment = "homelab"
    gateway_base_url: str
    node_fingerprint: str
    gateway_version: str
    hermes_version: str | None = None
    tags: list[str] = Field(default_factory=list)


class Node(BaseModel):
    node_id: str
    display_name: str
    environment: Environment
    gateway_base_url: str | None = None
    node_fingerprint: str | None = None
    gateway_version: str | None = None
    hermes_version: str | None = None
    health: Literal["online", "degraded", "offline", "unknown"]
    tags: list[str] = Field(default_factory=list)
    capabilities: list[Capability] = Field(default_factory=list)
    agents: list[Agent] = Field(default_factory=list)
    created_at: datetime | None = None
    last_seen_at: datetime | None = None


class DeviceRegistration(StrictModel):
    device_name: str
    platform: Platform
    app_instance_id: str
    app_version: str | None = None
    push_token: str | None = None


class Device(BaseModel):
    device_id: str
    node_id: str | None = None
    device_name: str
    platform: Platform
    status: DeviceStatus
    permissions: list[Permission]
    registered_at: datetime
    last_seen_at: datetime | None = None


class CreatePairingSessionRequest(StrictModel):
    display_name: str
    requested_permissions: list[Permission] = Field(default_factory=list)
    ttl_seconds: int | None = Field(default=None, ge=-1, le=3600)


class PairingSession(BaseModel):
    pairing_id: str
    pairing_token: str | None = None
    challenge: str
    status: Literal["pending", "completed", "expired", "cancelled"]
    node_id: str
    node_fingerprint: str
    expires_at: datetime


class CompletePairingRequest(StrictModel):
    pairing_id: str
    challenge_response: str
    device_public_key: str
    device: DeviceRegistration


class AuthTokenSet(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime


class CompletePairingResponse(BaseModel):
    node: Node
    device: Device
    tokens: AuthTokenSet


class RefreshTokenRequest(StrictModel):
    refresh_token: str
    signed_nonce: str


class Agent(BaseModel):
    agent_id: str
    node_id: str
    display_name: str
    agent_kind: str | None = None
    status: AgentStatus
    active_session_id: str | None = None
    current_tool: str | None = None
    current_target: str | None = None
    tags: list[str] = Field(default_factory=list)
    capabilities: list[Capability] = Field(default_factory=list)
    last_seen_at: datetime | None = None


class Session(BaseModel):
    session_id: str
    conversation_id: str | None = None
    node_id: str
    agent_id: str
    status: SessionStatus
    title: str | None = None
    summary: str | None = None
    current_plan: str | None = None
    current_tool: str | None = None
    current_target: str | None = None
    started_at: datetime
    updated_at: datetime | None = None


class ApprovalRequest(BaseModel):
    approval_id: str
    action_id: str
    node_id: str
    agent_id: str
    session_id: str
    requested_tool: str
    risk_level: RiskLevel
    risk_category: str | None = None
    summary: str
    full_payload_redacted: dict[str, Any]
    resource_scope: str | None = None
    state: ApprovalState
    expires_at: datetime
    options: list[str]
    decision_scope: ApprovalScope | None = None
    decided_at: datetime | None = None
    decision_metadata: dict[str, Any] | None = None


class CreateApprovalRequest(StrictModel):
    action_id: str
    agent_id: str
    session_id: str
    requested_tool: str
    risk_level: RiskLevel
    summary: str
    full_payload_redacted: dict[str, Any]
    node_id: str | None = None
    risk_category: str | None = None
    resource_scope: str | None = None
    options: list[str] = Field(default_factory=lambda: ["approve_once", "deny"])
    expires_at: datetime


class HermesApprovalRequestedRequest(StrictModel):
    requested_tool: str
    risk_level: RiskLevel
    summary: str
    payload_redacted: dict[str, Any]
    agent_id: str
    session_id: str
    expires_in_seconds: int = Field(ge=1, le=86_400)
    suggested_scopes: list[ApprovalScope] = Field(default_factory=lambda: ["once"])
    action_id: str | None = None
    node_id: str | None = None
    risk_category: str | None = None
    resource_scope: str | None = None


class ApprovalStatusRequest(StrictModel):
    approval_id: str


class ApprovalStatusResponse(BaseModel):
    approval_id: str
    state: ApprovalState
    selected_scope: ApprovalScope | None = None
    decided_at: datetime | None = None
    decision_metadata: dict[str, Any] | None = None


class ApprovalDecisionRequest(StrictModel):
    decision_id: str
    decision: Literal["approve", "deny"]
    scope: ApprovalScope
    control: Literal["pause", "kill_task", "kill_agent", "quarantine_agent"] | None = None
    signed_payload: dict[str, Any]
    signature: str


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    state: ApprovalState
    applied_scope: ApprovalScope | None = None


class InterventionRequest(StrictModel):
    intervention_id: str
    type: Literal[
        "pause",
        "resume",
        "inject_instruction",
        "cancel_task",
        "kill_task",
        "kill_agent",
        "quarantine_agent",
        "emergency_stop",
    ]
    reason: str
    instruction: str | None = None
    signed_payload: dict[str, Any]
    signature: str


class InterventionResponse(BaseModel):
    intervention_id: str
    resulting_state: str


class MobileNotifyRequest(StrictModel):
    title: str
    body: str
    urgency: NotificationUrgency
    category: NotificationCategory
    agent_id: str
    session_id: str
    action_id: str | None = None
    deep_link: str | None = None
    dedupe_key: str | None = None


class Notification(BaseModel):
    notification_id: str
    node_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    action_id: str | None = None
    category: NotificationCategory
    urgency: NotificationUrgency
    title_safe: str | None = None
    body_safe: str | None = None
    state: Literal["queued", "dispatched", "rate_limited", "deduped", "failed", "opened"]
    created_at: datetime


class AuditEvent(BaseModel):
    audit_event_id: str
    event_type: str
    actor_type: Literal["user", "device", "gateway", "hermes", "agent", "system"]
    actor_id: str
    node_id: str
    agent_id: str | None = None
    session_id: str | None = None
    approval_id: str | None = None
    notification_id: str | None = None
    voice_session_id: str | None = None
    request_id: str
    previous_hash: str | None = None
    hash: str
    payload_redacted: dict[str, Any] | None = None
    created_at: datetime


class EventEnvelope(BaseModel):
    event_id: str
    cursor: str
    node_id: str
    agent_id: str | None = None
    session_id: str | None = None
    conversation_id: str | None = None
    type: str
    severity: Literal["debug", "info", "warning", "error", "critical"] = "info"
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class Inventory(BaseModel):
    nodes: list[Node]
