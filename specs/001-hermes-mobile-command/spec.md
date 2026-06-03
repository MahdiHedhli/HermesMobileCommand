# Feature Specification: Hermes Mobile Command

**Feature Branch**: `001-hermes-mobile-command`
**Created**: 2026-06-03
**Status**: Draft
**Input**: Build a native iOS and Android mobile control plane for Hermes Agent installs. It must connect securely to one or more self-hosted Hermes nodes, preferably over Tailscale, provide chat and web-portal parity, show live agent activity, support mobile push notifications from Hermes, maintain an approval queue for risky actions, allow the user to pause/cancel/intervene in running agents, and eventually support live voice mode. Focus on user goals, safety requirements, acceptance criteria, and non-goals. Do not choose implementation details yet.

## User Scenarios & Testing

### Primary User Story

As the owner or operator of one or more Hermes installs, I want a mobile command surface that lets me talk to Hermes, monitor live agent work, receive urgent alerts, and approve or stop risky actions without exposing my self-hosted systems publicly.

### Acceptance Scenarios

1. **Given** the user has registered one Hermes node with the mobile app, **When** they open the app, **Then** they can see node health, active agents, recent sessions, and unread alerts for that node.
2. **Given** an agent is running on a registered Hermes node, **When** the agent emits activity events, **Then** the app shows a live activity stream with enough context for the user to understand the current task state.
3. **Given** Hermes requests approval for a risky action, **When** the user opens the approval queue, **Then** they can review the redacted payload, risk level, expiration, and available decisions before responding.
4. **Given** a risky action needs immediate attention, **When** Hermes sends a high or critical mobile notification, **Then** the user receives a push notification with a deep link to the relevant session or approval item.
5. **Given** the user is away from the web portal, **When** they need to intervene, **Then** they can pause the agent, terminate the task, deny an action, or send a message into the session from mobile.
6. **Given** the user manages multiple Hermes nodes, **When** they switch nodes, **Then** the app keeps node identity, agent identity, approval queues, audit history, and notification state clearly separated.

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
- **FR-004**: The app MUST provide parity with essential Hermes web-portal workflows required for mobile operation: session review, agent status, intervention, and approvals.
- **FR-005**: The app MUST show live agent activity for active sessions, including task state, current action, recent tool use summaries, and blocking conditions.
- **FR-006**: The app MUST maintain an approval queue for risky actions requested by Hermes agents.
- **FR-007**: Approval items MUST include action ID, agent ID, session ID, requested tool, risk level, human-readable summary, redacted payload, expiration time, and available response options.
- **FR-008**: The app MUST support approval responses: approve once, deny, approve for session, pause agent, and terminate task.
- **FR-009**: The app MUST allow the user to pause, cancel, or intervene in running agents from the relevant session view.
- **FR-010**: Hermes MUST be able to request urgent mobile notifications for approval requests, blocked tasks, security alerts, agent help requests, completed long-running tasks, and errors.
- **FR-011**: Notification requests MUST include title, body, urgency, category, agent ID, session ID, and optional action ID or deep link.
- **FR-012**: Low and normal urgency notifications MAY be batched; high urgency notifications MUST be sent promptly; critical notifications MUST request quiet-mode bypass where the user's OS and permissions allow it.
- **FR-013**: Every notification request, delivery attempt, approval request, approval decision, intervention, and policy denial MUST be recorded in an audit log.
- **FR-014**: Notification titles and bodies MUST NOT include secrets.
- **FR-015**: Hermes-side policy enforcement MUST evaluate requested mobile notifications and permissive actions before they are accepted.
- **FR-016**: The system MUST support secure operation without public internet exposure for self-hosted Hermes installs.
- **FR-017**: The default connectivity model MUST assume private network access, such as Tailscale-only access.
- **FR-018**: HTTPS relay support MAY be introduced later, but MUST NOT become required for self-hosted installs.
- **FR-019**: The app MUST present node, agent, session, approval, notification, and audit data in a way that avoids confusing one Hermes install with another.
- **FR-020**: The product MUST reserve room for future voice interaction and live voice intervention without requiring voice support in the first release.

### Safety Requirements

- **SR-001**: The mobile app MUST be treated as a safety and intervention surface, not only as a passive monitoring UI.
- **SR-002**: The user MUST be able to identify the node, agent, session, requested action, risk level, and expiration before approving any risky action.
- **SR-003**: Approval payloads shown on mobile MUST be redacted before display.
- **SR-004**: The system MUST deny or quarantine approval requests that lack required identity, risk, summary, expiration, or redaction fields.
- **SR-005**: Approval decisions MUST be scoped explicitly to the selected action or session and MUST NOT silently broaden to other nodes, agents, or future sessions.
- **SR-006**: Critical operations MUST remain auditable even if the user responds from a push notification or deep link.
- **SR-007**: The system MUST prevent secrets from being included in mobile notification title or body fields.
- **SR-008**: The system MUST fail closed for unavailable, expired, malformed, or policy-denied approval requests.
- **SR-009**: A user intervention such as pause agent or terminate task MUST produce visible confirmation and an audit entry.
- **SR-010**: The product MUST NOT require users to expose self-hosted Hermes nodes to the public internet.

## Hermes-Side Event & Tool Model

### `mobile_notify`

Hermes can request an urgent mobile push notification to the owner.

Required fields:

- `title`: string
- `body`: string
- `urgency`: `low` | `normal` | `high` | `critical`
- `category`: `approval_required` | `task_blocked` | `security_alert` | `agent_needs_help` | `long_running_task_done` | `error`
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
- `options`: one or more of `approve_once`, `deny`, `approve_for_session`, `pause_agent`, `terminate_task`

## Key Entities

- **Hermes Node**: A registered Hermes install that can stream events, accept chat, request approvals, and send notification requests.
- **Agent**: A Hermes agent running work within a session.
- **Session**: A bounded conversation or task execution context associated with a node and agent activity.
- **Approval Request**: A time-limited request for user authorization before a risky action proceeds.
- **Notification Request**: A Hermes-originated request to alert the mobile user.
- **Audit Entry**: An immutable record of notification requests, approval decisions, interventions, policy denials, and relevant gateway actions.
- **Mobile Gateway**: The Hermes-side component responsible for node registration, event streaming, approval queue maintenance, notification exposure, message relay, audit logging, and policy enforcement.

## Success Criteria

- **SC-001**: A user can register at least one self-hosted Hermes node and verify its current connection state from mobile.
- **SC-002**: A user can send and receive Hermes chat messages from mobile for an active session.
- **SC-003**: A user can see active agent sessions and understand what each agent is currently doing without using the web portal.
- **SC-004**: A user can receive a push notification for an approval-required event and navigate directly to the related approval item.
- **SC-005**: A user can approve once, deny, approve for session, pause the agent, or terminate the task for a pending approval request.
- **SC-006**: Expired or malformed approval requests cannot be approved.
- **SC-007**: Notification and approval activity is visible in an audit trail.
- **SC-008**: The first release works for self-hosted users without requiring public exposure of their Hermes node.

## Non-Goals

- Building a public-hosted Hermes control plane.
- Requiring a cloud relay for self-hosted installs.
- Replacing the Hermes web portal for every administrative workflow.
- Choosing mobile framework, backend framework, database, push provider, or protocol implementation details in this specification.
- Implementing full live voice mode in the first release.
- Supporting arbitrary third-party agent systems outside Hermes.
- Allowing unredacted tool payloads or secrets in mobile notifications.
- Treating push notifications as the only durable source of approval or audit state.

## Open Questions

- What exact Hermes web-portal workflows are required for minimum mobile parity?
- What policy rules define low, medium, high, and critical risk for approval requests?
- What redaction rules are mandatory before payloads reach the mobile app?
- How should notification batching behave across multiple nodes and agents?
- What user identity and device enrollment model should govern access to nodes?
- What audit retention and export expectations apply to self-hosted installs?
