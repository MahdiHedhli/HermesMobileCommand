# Feature Specification: Hermes Mobile Control Plane

**Feature Branch**: `001-hermes-mobile-command`
**Created**: 2026-06-03
**Status**: Draft
**Input**: Build a native iOS and Android mobile control plane for Hermes Agent installs. It must connect securely to one or more self-hosted Hermes nodes, preferably over Tailscale, provide chat and web-portal parity, show live agent activity, support mobile push notifications from Hermes, maintain an approval queue for risky actions, allow the user to pause/cancel/intervene in running agents, and eventually support live voice mode. Focus on user goals, safety requirements, acceptance criteria, and non-goals. Do not choose implementation details yet.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Approve and Intervene on Risky Actions (Priority: P1)

As the owner or operator of Hermes installs, I want a mobile approval and intervention queue so I can safely approve, deny, pause, or terminate risky agent activity while away from the web portal.

**Why this priority**: This is the primary mobile differentiator and the highest safety value: the app becomes the user's always-available control point for risky agent behavior.

**Independent Test**: Can be tested by emitting a pending approval request from a registered node and confirming the user can understand the request, select a decision, and see the resulting state and audit entry without using the web portal.

**Acceptance Scenarios**:

1. **Given** Hermes requests approval for a risky action, **When** the user opens the approval queue, **Then** they can review the redacted payload, risk level, expiration, and available decisions before responding.
2. **Given** the user chooses an approval response, **When** the response is submitted, **Then** Hermes receives the selected decision and the app records the decision in the audit trail.
3. **Given** the approval request is expired, malformed, unavailable, or policy-denied, **When** the user views it, **Then** the app prevents approval and explains the blocked state.
4. **Given** the user needs to stop active work, **When** they choose pause agent or terminate task, **Then** the selected agent or task is stopped according to the chosen intervention and the action is audited.

---

### User Story 2 - Monitor and Chat With Live Agents (Priority: P2)

As a Hermes operator, I want to see live agent activity, chat with Hermes, review artifacts, and inspect session context from mobile so I can understand what is happening and guide work without opening the web portal.

**Why this priority**: Approval decisions need context. Monitoring and chat make mobile intervention useful rather than blind.

**Independent Test**: Can be tested by starting an agent session, streaming activity into the app, sending a mobile chat message, and confirming the user can understand and influence the session.

**Acceptance Scenarios**:

1. **Given** an agent is running on a registered Hermes node, **When** the agent emits activity events, **Then** the app shows a live activity stream with enough context for the user to understand the current task state.
2. **Given** the user opens an active session, **When** they send a message, **Then** Hermes receives the message in the correct node, agent, and session context.
3. **Given** an agent becomes blocked, **When** the user views the session, **Then** the blocked condition is visible and tied to the relevant agent activity.
4. **Given** a session has files, artifacts, memory references, skill usage, browser state, logs, or tool history, **When** the user opens the session view, **Then** the app exposes those details at a level suitable for mobile review.

---

### User Story 3 - Receive Urgent Mobile Notifications (Priority: P3)

As a Hermes owner, I want urgent push notifications for approvals, blocked tasks, security alerts, and errors so important agent events reach me even when the app is closed.

**Why this priority**: Mobile value depends on timely interruption for the events that need human attention.

**Independent Test**: Can be tested by sending notification requests with each supported category and urgency and confirming delivery behavior, deep-link routing, secret filtering, and audit logging.

**Acceptance Scenarios**:

1. **Given** a risky action needs immediate attention, **When** Hermes sends a high or critical mobile notification, **Then** the user receives a push notification with a deep link to the relevant session or approval item.
2. **Given** Hermes sends low or normal urgency notifications, **When** batching is appropriate, **Then** the app may group notifications without losing the underlying audit history.
3. **Given** a notification request contains secrets in the title or body, **When** the request is evaluated, **Then** the system prevents those secrets from reaching the mobile notification.

---

### User Story 4 - Manage Multiple Hermes Nodes (Priority: P4)

As a user with multiple Hermes installs, I want a multi-agent command center so I can label environments, compare active work, and move or redirect work without confusing agents, sessions, approvals, notifications, or audits.

**Why this priority**: Multi-node support is central to the product scope, but it can follow the core approval, monitoring, and notification workflows.

**Independent Test**: Can be tested by registering multiple nodes with overlapping agent and session identifiers and confirming every action remains scoped to the selected node.

**Acceptance Scenarios**:

1. **Given** the user has registered one Hermes node with the mobile app, **When** they open the app, **Then** they can see node health, active agents, recent sessions, and unread alerts for that node.
2. **Given** the user manages multiple Hermes nodes, **When** they switch nodes, **Then** the app keeps node identity, agent identity, approval queues, audit history, and notification state clearly separated.
3. **Given** one node is unreachable, **When** other nodes remain reachable, **Then** the unreachable node does not block monitoring or approvals for the reachable nodes.
4. **Given** a user labels agents or nodes by environment, **When** they view the global command center, **Then** those labels help distinguish homelab, VPS, laptop, work VM, and other operator-defined environments.
5. **Given** a conversation or task should move to another agent, **When** the user redirects it, **Then** the app records the transfer and keeps the source and destination contexts clear.

---

### User Story 5 - Prepare for Future Voice Intervention (Priority: P5)

As a mobile Hermes user, I want the product direction to include push-to-talk, continuous voice conversation, and voice-based approval so I can eventually speak with or interrupt Hermes during live work.

**Why this priority**: Voice is strategically important, but it is explicitly not required for the first release.

**Independent Test**: Can be tested at the specification level by confirming first-release workflows do not depend on voice and that voice-facing intervention concepts are represented in product scope for future planning.

**Acceptance Scenarios**:

1. **Given** the first release is being evaluated, **When** voice support is unavailable, **Then** all required chat, monitoring, notification, and approval workflows still work.
2. **Given** future planning begins for voice mode, **When** product requirements are reviewed, **Then** voice interaction and live intervention are already represented as future product goals.
3. **Given** voice approval becomes available later, **When** the user approves a consequential action by voice, **Then** the system requires a confirmation phrase before recording the approval.

### Edge Cases

- A node is temporarily unreachable while an approval is pending.
- An approval request expires before the user responds.
- A notification is delivered after the related session has ended.
- A node sends malformed, incomplete, duplicate, or stale events.
- A user is connected to multiple nodes with overlapping agent or session identifiers.
- The app is offline when Hermes emits urgent activity.
- A push notification payload attempts to include secrets or sensitive values.
- A critical notification is requested while the OS is enforcing quiet mode or notification limits.

## Requirements

### Functional Requirements

- **FR-001**: The app MUST allow the user to register and manage multiple Hermes nodes.
- **FR-002**: The app MUST show each registered node's identity, connection state, last contact time, and high-level health.
- **FR-003**: The app MUST provide a chat surface for communicating with Hermes from mobile.
- **FR-004**: The app MUST provide parity with essential Hermes web-portal workflows required for mobile operation: conversations, sessions, files, artifacts, skills, memory visibility, tool run history, browser or session viewer, agent status, logs, intervention, and approvals.
- **FR-005**: The app MUST show live agent activity for active sessions, including task state, current plan, current tool, current target, recent tool use summaries, terminal output where available, browser or session state where available, and blocking conditions.
- **FR-006**: The app MUST maintain an approval queue for risky actions requested by Hermes agents.
- **FR-007**: Approval items MUST include action ID, agent ID, session ID, requested tool, risk level, human-readable summary, redacted payload, expiration time, and available response options.
- **FR-008**: The app MUST support approval responses: approve once, approve for this session, approve for this agent, approve permanent policy exception, deny, always deny, pause agent, and terminate task.
- **FR-009**: The app MUST allow the user to start, pause, cancel, redirect, freeze, or intervene in running agents from the relevant session view.
- **FR-010**: Hermes MUST be able to request urgent mobile notifications for approval requests, blocked tasks, security alerts, agent help requests, completed long-running tasks, and errors.
- **FR-011**: Notification requests MUST include title, body, urgency, category, agent ID, session ID, and optional action ID or deep link.
- **FR-012**: Low and normal urgency notifications MAY be batched; high urgency notifications MUST be sent promptly; critical notifications MUST request quiet-mode bypass where the user's OS and permissions allow it.
- **FR-013**: Every notification request, delivery attempt, approval request, approval decision, intervention, and policy denial MUST be recorded in an audit log.
- **FR-014**: Notification titles and bodies MUST NOT include secrets.
- **FR-015**: Hermes-side policy enforcement MUST evaluate requested mobile notifications and permissive actions before they are accepted.
- **FR-016**: The system MUST support secure operation without public internet exposure for self-hosted Hermes installs.
- **FR-017**: The default connectivity model MUST assume private network access, with Tailscale as the preferred path and trusted local network access as an acceptable self-hosted path.
- **FR-018**: HTTPS or hosted relay support MAY be introduced later, but MUST NOT become required for self-hosted installs.
- **FR-019**: The app MUST present node, agent, session, approval, notification, and audit data in a way that avoids confusing one Hermes install with another.
- **FR-020**: The product MUST reserve room for future voice interaction and live voice intervention without requiring voice support in the first release.
- **FR-021**: The app MUST allow the user to label nodes and agents by environment or purpose.
- **FR-022**: The app MUST show a global activity dashboard across registered Hermes nodes.
- **FR-023**: The app MUST support an emergency stop action that freezes or stops consequential agent work pending review.
- **FR-024**: The app MUST allow the user to inject an instruction into a running session.
- **FR-025**: The app SHOULD support taking over a browser or control session when Hermes exposes a controllable live session.
- **FR-026**: The product SHOULD support moving or redirecting a conversation or task between agents when both source and destination agents allow transfer.

### Key Entities

- **Hermes Node**: A registered Hermes install that can stream events, accept chat, request approvals, and send notification requests.
- **Agent**: A Hermes agent running work within a session.
- **Session**: A bounded conversation or task execution context associated with a node and agent activity.
- **Approval Request**: A time-limited request for user authorization before a risky action proceeds.
- **Notification Request**: A Hermes-originated request to alert the mobile user.
- **Audit Entry**: An immutable record of notification requests, approval decisions, interventions, policy denials, and relevant gateway actions.
- **Hermes Control Gateway**: The Hermes-side sidecar responsible for node registration, event streaming, approval queue maintenance, notification exposure, message relay, audit logging, and policy enforcement.

### Safety Requirements

- **SR-001**: The mobile app MUST be treated as a safety and intervention surface, not only as a passive monitoring UI.
- **SR-002**: The user MUST be able to identify the node, agent, session, requested action, risk level, and expiration before approving any risky action.
- **SR-003**: Approval payloads shown on mobile MUST be redacted before display.
- **SR-004**: The system MUST deny or quarantine approval requests that lack required identity, risk, summary, expiration, or redaction fields.
- **SR-005**: Approval decisions MUST be scoped explicitly to the selected action, session, agent, or permanent policy exception and MUST NOT silently broaden to other nodes, agents, tasks, or future sessions.
- **SR-006**: Critical operations MUST remain auditable even if the user responds from a push notification or deep link.
- **SR-007**: The system MUST prevent secrets from being included in mobile notification title or body fields.
- **SR-008**: The system MUST fail closed for unavailable, expired, malformed, or policy-denied approval requests.
- **SR-009**: A user intervention such as pause agent or terminate task MUST produce visible confirmation and an audit entry.
- **SR-010**: The product MUST NOT require users to expose self-hosted Hermes nodes to the public internet.
- **SR-011**: Approval requests MUST be attributable and tamper-evident, with clear action scope, risk category, expiration, and requesting agent identity.
- **SR-012**: The system MUST escalate actions involving shell execution, browser submission, file deletion, email sending, repository push, payment, credential access, network scanning, and similar consequential operations.
- **SR-013**: Emergency stop MUST remain available from active task and approval contexts and MUST create a visible audit entry.
- **SR-014**: Voice approval, when introduced, MUST require explicit confirmation before a consequential action is approved.

## Hermes-Side Event & Tool Model

### `mobile_notify`

Hermes can request an urgent mobile push notification to the owner.

Required fields:

- `title`: string
- `body`: string
- `urgency`: `low` | `normal` | `high` | `critical`
- `category`: `approval_required` | `security_alert` | `agent_blocked` | `task_complete` | `system_health` | `voice_callback`
- `agent_id`: string
- `session_id`: string

Optional fields:

- `action_id`: string
- `deep_link`: string

Behavior:

- Low and normal urgency notifications may batch.
- High urgency notifications send immediately.
- Critical notifications request quiet-mode bypass where the OS allows.
- Every notification is logged.
- Notification title and body cannot include secrets.

### `approval_requested`

Hermes emits an approval request when an agent needs human authorization before continuing.

Required fields:

- `action_id`: string
- `agent_id`: string
- `session_id`: string
- `requested_tool`: string
- `risk_level`: `low` | `medium` | `high` | `critical`
- `summary`: string
- `full_payload_redacted`: object
- `expires_at`: datetime
- `options`: one or more of `approve_once`, `approve_for_session`, `approve_for_agent`, `approve_permanent`, `deny`, `always_deny`, `pause_agent`, `terminate_task`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can register a reachable self-hosted Hermes node and confirm its connection state from mobile in under 5 minutes.
- **SC-002**: A user can identify what an active agent is doing from the mobile session view in under 30 seconds during usability testing.
- **SC-003**: A user can navigate from an approval-required push notification to the exact approval item in 2 interactions or fewer.
- **SC-004**: A user can submit any supported approval response for a pending approval request without using the web portal.
- **SC-005**: 100% of expired, malformed, unavailable, or policy-denied approval requests are prevented from being approved.
- **SC-006**: 100% of notification requests, approval decisions, interventions, and policy denials create audit entries containing node, agent, and session context when available.
- **SC-007**: A user can manage at least 3 registered Hermes nodes and correctly distinguish their sessions, approvals, and notifications during testing.
- **SC-008**: The first release supports self-hosted operation with no requirement for public internet exposure of a Hermes node.
- **SC-009**: A user can trigger emergency stop for an active consequential task in 2 interactions or fewer from the active task or approval context.
- **SC-010**: A user can inspect the current plan, current tool, current target, and recent output for an active task without opening the web portal.

## Non-Goals

- Building a public-hosted Hermes control plane.
- Requiring a cloud relay for self-hosted installs.
- Replacing the Hermes web portal for every administrative workflow outside mobile control, monitoring, approval, and intervention needs.
- Choosing mobile framework, backend framework, database, push provider, or protocol implementation details in this specification.
- Implementing full live voice mode in the first release.
- Supporting arbitrary third-party agent systems outside Hermes.
- Allowing unredacted tool payloads or secrets in mobile notifications.
- Treating push notifications as the only durable source of approval or audit state.

## Assumptions

- The primary first-release user is the owner or trusted operator of one or more Hermes installs.
- Hermes already has web-portal workflows, rich tools, browser automation, TTS, and multi-surface access; this product focuses on mobile safety, notification, approval, and intervention workflows.
- A Hermes Control Gateway sidecar is part of the product scope and is responsible for registration, event streaming, approval queue maintenance, notification exposure, message relay, audit logging, and policy enforcement.
- The first release prioritizes private connectivity for self-hosted installs; relay-based access is a later option and not a launch dependency.
- The mobile app is allowed to receive push notifications after the user enrolls the device and grants the necessary OS-level permissions.
- Voice interaction is a future capability and must not block the first release.
- The product name for documentation and positioning is Hermes Mobile Control Plane, even if repository or feature branch names retain an earlier short name.

## Related Adoption References

- [Hermes Wingman adoption matrix](../../docs/adoption/hermes-wingman-adoption-matrix.md)
- [Hermes Wingman architecture delta](../../docs/adoption/hermes-wingman-architecture-delta.md)
- [Hermes Wingman UI inventory](../../docs/adoption/hermes-wingman-ui-inventory.md)
- [Hermes Wingman backend/API lessons](../../docs/adoption/hermes-wingman-backend-lessons.md)

## Open Questions

- What exact Hermes web-portal workflows are required for minimum mobile parity?
- What policy rules define low, medium, high, and critical risk for approval requests?
- What redaction rules are mandatory before payloads reach the mobile app?
- How should notification batching behave across multiple nodes and agents?
- What user identity and device enrollment model should govern access to nodes?
- What audit retention and export expectations apply to self-hosted installs?
- Which approval scopes are allowed for each high-risk action category?
- Under what conditions may tasks or conversations move between agents?
