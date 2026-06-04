# Build Roadmap

## Purpose

This roadmap sequences implementation so each phase delivers independently testable value while preserving the long-term architecture.

## Cross-Phase Foundations

These foundations should begin before or during Phase 1:

- Hermes Control Gateway skeleton
- Device pairing and node identity
- Local audit log
- Event envelope format
- Capability registry
- Mobile secure storage
- Basic diagnostics and health endpoints

## Phase 1: Read-Only Observer

Scope:

- Connect to one Hermes node over Tailscale or trusted local network.
- Pair one mobile device.
- Show node health.
- Show agent list.
- Show sessions, active task, status, and logs.
- Stream or poll live activity read-only.

Acceptance criteria:

- User can register one node in under 5 minutes.
- User can view active agent status without web portal.
- User can see current task/log state.
- Lost connectivity is visible.
- Read-only actions create audit entries where relevant.

Risks:

- Hermes internal event surfaces may be incomplete.
- Gateway event normalization may need adapter work.
- Mobile backgrounding may interrupt live stream.

Dependencies:

- Gateway health API.
- Pairing flow.
- Agent/session inventory adapter.
- Event stream or polling fallback.

## Phase 2: Chat

Scope:

- Send messages from mobile to Hermes sessions.
- Stream responses.
- View conversation history.
- View files/artifacts metadata and safe previews.

Acceptance criteria:

- User can send and receive messages in an active session.
- Streamed responses reconcile after reconnect.
- Artifacts are visible with redaction and size limits.
- Node/agent/session context is visible for every message.

Risks:

- Chat parity may reveal more web-portal scope than MVP should take.
- Artifact preview may expose sensitive content.
- Concurrent messages across devices need ordering rules.

Dependencies:

- Conversation/message API.
- Event backfill.
- Redaction policy.
- Session context mapping.

## Phase 3: Approvals

Scope:

- Approval queue.
- Approval detail.
- Risk levels and scopes.
- Signed approval decisions.
- Push notification for pending approvals.
- Pause/kill task from approval context.
- Audit trail for approvals and decisions.

Acceptance criteria:

- User can approve or deny a pending approval.
- Expired/malformed approvals fail closed.
- Signed decisions bind exact action and scope.
- Push notification deep links to approval detail.
- Every decision is audited.

Risks:

- Policy design may under-classify risky actions.
- Secret redaction must be reliable before push/mobile display.
- Lost phone and token theft scenarios need thorough review.

Dependencies:

- Device key registration.
- Approval engine.
- Push dispatcher.
- Audit log.
- Hermes tool execution gate.

## Phase 4: Multi-Agent

Scope:

- Register multiple Hermes installs.
- Global dashboard.
- Agent grouping by environment.
- Tags and capabilities.
- Multi-node approval and notification separation.

Acceptance criteria:

- User can manage at least 3 nodes.
- Duplicate agent/session IDs across nodes do not conflict.
- Dashboard clearly separates environments.
- Node unreachable state does not block other nodes.

Risks:

- Mobile inventory can become stale.
- Cross-node task transfer can leak context if added too early.
- Notification noise increases with node count.

Dependencies:

- Inventory schema.
- Node-scoped auth tokens.
- Per-node event cursors.
- Notification dedupe by node/agent/session.

## Phase 5: Intervention

Scope:

- Pause agent.
- Resume agent.
- Inject instruction.
- Cancel task.
- Kill task.
- Quarantine agent.
- Browser/session viewer.
- Browser/session takeover where Hermes supports it.

Acceptance criteria:

- User can pause or cancel active work from live activity.
- User can inject an instruction mid-run.
- Emergency stop applies in 2 interactions or fewer.
- Browser/session takeover is gated by capability and audited.
- Intervention state is reflected in live activity.

Risks:

- Hermes may not expose uniform control hooks across agents.
- Browser takeover can create session hijack risk.
- Killing tasks may leave external side effects incomplete.

Dependencies:

- Intervention API.
- Hermes runtime control hooks.
- Browser subsystem adapter.
- Strong audit and confirmation UX.

## Phase 6: Voice

Scope:

- Push-to-talk first.
- Voice session screen.
- Hermes voice mode bridge.
- Optional TTS response.
- Half-duplex later.
- Full duplex/WebRTC later.
- Voice approval with confirmation phrase in a later phase.

Acceptance criteria:

- User can send a push-to-talk voice instruction.
- Voice session is tied to node, agent, and session.
- Text controls remain available if voice fails.
- Voice approval cannot bypass normal approval signing.

Risks:

- Voice providers may expose sensitive transcripts/audio.
- Mobile audio permissions and background behavior are platform-specific.
- Full-duplex voice adds substantial signaling and media complexity.

Dependencies:

- Voice coordinator.
- Hermes voice adapter.
- Audio upload/stream transport.
- Voice audit events.
- Approval signing for future voice approval.

## Deferral List

Explicitly deferred:

- UI polish and branding.
- Payment systems.
- SaaS business model.
- Public cloud relay implementation.
- Production deployment automation.
- Enterprise SSO and RBAC beyond schema readiness.

## Readiness Gates

Before implementation begins:

- API contract reviewed by gateway and mobile teams.
- Threat model reviewed for approval and push paths.
- Hermes integration points identified for events, tools, browser, and voice.
- Data retention defaults accepted by project owner.
- ADRs accepted or revised.
