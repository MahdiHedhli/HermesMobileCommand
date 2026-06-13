# Platform Roadmap

Sprint: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`

This roadmap replaces the feature-slice view with a platform-centric path. The historical slice roadmap remains in [roadmap.md](roadmap.md).

## Phase A: Native Validation And Production Hardening

Goal:

- Make the current product reliable on native mobile targets and reduce security ambiguity.

Scope:

- Complete iOS and Android toolchain validation.
- Validate secure storage on iOS Keychain and Android Keystore.
- Add first-class CapabilityGrant model and revocation UX.
- Add OperatorSession projection for intervention summaries.
- Split gateway routers and storage domains.
- Add endpoint maturity labels to OpenAPI.
- Harden WebSocket auth and attach-token patterns.

Exit criteria:

- iOS and Android app launches against a local gateway.
- Signed approval flow works on at least one iOS and one Android target.
- TUI remains development-only unless explicitly enabled.
- Gateway and Flutter validation pass on the beta branch.

## Phase B: Real Hermes Runtime Integration

Goal:

- Move from local smoke paths to real Hermes runtime operation.

Scope:

- Build on the Runtime Integration 007 adapter boundary and the Runtime Client 008 blocking helpers.
- Wire `HermesRuntimeClient` into Hermes runtime/tool policy.
- Make approval, notification, TUA, browser assistance, and voice helpers consumable by blocked Hermes actions.
- Expand the durable Mission projection into timelines mapped from Hermes sessions/tasks.
- Feed richer live agent activity into Home, Missions, Agent Detail, and Inbox.
- Make assistance return-control summaries actionable by Hermes.
- Improve gateway registration and health reporting for many nodes.

Exit criteria:

- A real Hermes action can block on mobile approval and resume/deny correctly.
- A real Hermes task can request TUA or browser assistance and receive returned control.
- Mission timelines include events, approvals, assistance, notifications, and audit references.
- Runtime polling can be replaced or supplemented by callback delivery where blocking wait helpers are insufficient.

## Phase C: Browser Streaming And Voice Audio

Goal:

- Turn assistance prototypes into high-value live operator modes.

Scope:

- Add browser screenshot or stream transport.
- Add safe browser take-over protocol and return-control contract.
- Add mobile voice recording for supported targets.
- Add push-to-talk audio capture and playback.
- Evaluate WebRTC for browser and voice streaming.
- Keep all live media modes self-hosted and Tailscale-first.

Exit criteria:

- Operator can inspect browser state during a blocked web action.
- Operator can send voice input without external provider dependency.
- Streaming modes have clear permissions, audit metadata, and failure states.

## Phase D: Fleet Operations And Mission Management

Goal:

- Make Hermes Mobile Control Plane useful across many nodes and agents.

Scope:

- Durable Mission CRUD/read model.
- Fleet health and capability inventory.
- Team grouping polish.
- Agent quarantine/release workflow.
- Mission transfer or redirect design.
- Search and filters across agents, missions, notifications, approvals, and audit events.

Exit criteria:

- Operator can understand all active Hermes work from Home and Missions.
- Fleet-level degraded states and blocked agents are obvious.
- Mission history is coherent across nodes.

## Phase E: Multi-User And Enterprise Readiness

Goal:

- Prepare the platform for shared operations without optimizing for enterprise too early.

Scope:

- User identities beyond the implicit owner.
- Role-based device permissions.
- Multi-device conflict and delegation handling.
- Audit export and retention controls.
- Policy review workflow for ApprovalPolicyProposal.
- Organization-level team and node ownership model.

Exit criteria:

- Multiple operators can safely view and act within scoped permissions.
- Approval and policy actions show accountable user/device identity.
- Audit records support review and incident response.

## Phase F: Agent Operations Platform

Goal:

- Grow beyond mobile companion into a full operations layer for self-hosted AI agents.

Scope:

- Cross-agent mission orchestration.
- Safety policy authoring and simulation.
- Operator-session analytics.
- Fleet-level incident response.
- Long-running task supervision.
- Optional relay or hosted coordination only when self-hosted defaults remain intact.

Exit criteria:

- Hermes Mobile Control Plane can supervise many Hermes installs as a coherent agent operations platform.
- The mobile app remains the highest-signal intervention surface.
- Public exposure remains optional, never required.

## Top Three Implementation Priorities

1. Native validation with real secure storage and signed approval flow on iOS/Android.
2. OperatorSession plus CapabilityGrant consolidation in gateway and mobile summaries.
3. Real Hermes runtime handoff for approvals, notifications, and assistance return-control.
