# Agentic Control Tower Documentation

Agentic Control Tower (ACT) is the control tower for agentic actions. It grants
clearances, denies clearances, sequences work, tracks state, and keeps the
audit log. Backends and agents remain the aircraft; ACT does not fly them or
execute their actions.

Hermes is adapter #1. Hermes-specific implementation and adoption documents are
retained where they describe real Hermes integration, but the generic runtime
boundary is the backend-neutral `RuntimeAdapter` seam.

## Start Here

- [Product assessment](product/product-assessment.md)
- [System architecture](architecture/system-architecture.md)
- [Threat model](security/threat-model.md)
- [API contract](api/openapi.yaml)
- [Roadmap](roadmap-next.md)
- [Parking lot](parking-lot.md)

## Core Documents

- [Feature specification](../specs/001-hermes-mobile-command/spec.md)
- [Product framing](mobile-control-plane-framing.md)
- [Service boundaries](architecture/service-boundaries.md)
- [Domain model review](architecture/domain-model-review.md)
- [Operator session review](architecture/operator-session-review.md)
- [Technical debt review](architecture/technical-debt-review.md)
- [Authentication and authorization](security/auth-authorization.md)
- [Clearance channel policy](security/clearance-channel-policy.md)
- [Runtime integration security review](security/runtime-integration-review.md)
- [Approval framework](architecture/approval-framework.md)
- [Advanced approval actions](architecture/advanced-approval-actions.md)
- [Push notification framework](architecture/push-notification-framework.md)
- [Event streaming architecture](architecture/event-streaming.md)
- [Multi-agent control plane](architecture/multi-agent-control-plane.md)
- [Teams and agent grouping](architecture/teams-agent-grouping.md)
- [TUI architecture](architecture/tui-architecture.md)
- [TUA architecture](architecture/tua-architecture.md)
- [Voice architecture](architecture/voice-architecture.md)
- [Data model](data-model.md)
- [Mobile UX architecture](mobile-ux-architecture.md)
- [UX consistency review](ux/ux-consistency-review.md)
- [Approval experience review](ux/approval-experience-review.md)
- [Historical build roadmap](roadmap.md)
- [Beta readiness assessment](release/beta-readiness.md)
- [Demo gallery](demo/demo-gallery.md)

## Runtime Adapter

The RuntimeAdapter seam translates backend-specific requests into ACT concepts:

- work state
- notices
- clearance requests
- clearance decisions
- operator handoffs
- return-of-control summaries

Hermes-specific adapter code may still use Hermes mission, session, and tool
language internally because that is the backend it adapts. Generic tower
interfaces should use ACT language: tower, backend, subject, adapter, operator,
clearance, handoff, and audit.

## Implementation Slices

- [Slice 001: Gateway foundation](implementation/slice-001-gateway-foundation.md)
- [Slice 003: Hermes integration and mobile readiness](implementation/slice-003-hermes-integration-mobile-readiness.md)
- [Mobile alpha UI](implementation/mobile-alpha-ui.md)
- [Mobile realness 002](implementation/mobile-realness-002.md)
- [Native readiness](implementation/native-readiness.md)
- [Mobile native realtime 003](implementation/mobile-native-realtime-003.md)
- [TUI PTY prototype 004](implementation/tui-pty-prototype-004.md)
- [Operator capabilities mega slice 005](implementation/operator-capabilities-mega-slice-005.md)
- [Runtime integration 007](implementation/runtime-integration-007.md)
- [Real Hermes client integration 008](implementation/real-hermes-client-008.md)
- [Real Hermes desktop discovery 009](implementation/real-hermes-desktop-discovery-009.md)
- [ACT-003 security hardening](implementation/act-003-security-hardening.md)
- [Runtime integration QA](qa/runtime-integration-qa.md)

## Feature Specifications

- [Spec 001: Hermes-origin control plane spec](../specs/001-hermes-mobile-command/spec.md)
- [Spec 002: TUI, TUA, Teams, and Advanced Approval UX](../specs/002-tui-tua-ux/spec.md)

## Adoption Audits

- [Hermes Wingman adoption matrix](adoption/hermes-wingman-adoption-matrix.md)
- [Hermes Wingman architecture delta](adoption/hermes-wingman-architecture-delta.md)
- [Hermes Wingman UI inventory](adoption/hermes-wingman-ui-inventory.md)
- [Hermes Wingman backend/API lessons](adoption/hermes-wingman-backend-lessons.md)

## Architecture Decision Records

- [ADR-0001: Tailscale-first self-hosted connectivity](adr/0001-tailscale-first-self-hosted-connectivity.md)
- [ADR-0002: Gateway sidecar per Hermes install](adr/0002-gateway-sidecar-per-hermes-install.md)
- [ADR-0003: Device key pairing and signed approvals](adr/0003-device-key-pairing-and-signed-approvals.md)
- [ADR-0004: WebSocket primary event stream](adr/0004-websocket-primary-event-stream.md)
- [ADR-0005: Push notifications are hints, not durable state](adr/0005-push-notifications-are-hints-not-state.md)
- [ADR-0006: Approval engine fails closed](adr/0006-approval-engine-fails-closed.md)
- [ADR-0007: Local append-only audit log](adr/0007-local-append-only-audit-log.md)
- [ADR-0008: Staged voice architecture](adr/0008-staged-voice-architecture.md)
- [ADR-0009: Hermes Wingman adoption policy](adr/0009-hermes-wingman-adoption-policy.md)
- [ADR-0010: SQLite local gateway storage for first slice](adr/0010-sqlite-local-gateway-storage-for-first-slice.md)
- [ADR-0011: Ed25519 canonical device request signing](adr/0011-ed25519-canonical-device-request-signing.md)
- [ADR-0012: TUI as first-class mobile subsystem](adr/0012-tui-first-class-mobile-subsystem.md)
- [ADR-0013: TUA as separate assistance subsystem](adr/0013-tua-separate-assistance-subsystem.md)
- [ADR-0014: Agents v1 terminology with Teams grouping](adr/0014-agents-v1-terminology-teams-grouping.md)
- [ADR-0015: Modified and conditional approval decisions](adr/0015-modified-conditional-approval-decisions.md)

## Team Boundaries

- Gateway/runtime adapter team: system architecture, API contract, clearance
  framework, data model, threat model.
- Mobile app teams: mobile UX architecture, API contract, auth design, push
  framework, voice phases.
- Approval/clearance team: approval framework, auth design, data model, ADRs.
- Push team: push framework, threat model, audit and rate-limit requirements.
- Hermes adapter team: Hermes-specific runtime integration and desktop discovery.
