# Hermes Mobile Control Plane Architecture Package

Sprint: `HERMES-MCP-ARCHITECTURE-FOUNDATION-001`

This package turns the Hermes Mobile Control Plane feature specification into an implementation-ready engineering foundation.

## Core Documents

- [Feature specification](../specs/001-hermes-mobile-command/spec.md)
- [Product framing](mobile-control-plane-framing.md)
- [System architecture](architecture/system-architecture.md)
- [Service boundaries](architecture/service-boundaries.md)
- [Threat model](security/threat-model.md)
- [Authentication and authorization](security/auth-authorization.md)
- [Approval framework](architecture/approval-framework.md)
- [Push notification framework](architecture/push-notification-framework.md)
- [Event streaming architecture](architecture/event-streaming.md)
- [Multi-agent control plane](architecture/multi-agent-control-plane.md)
- [Voice architecture](architecture/voice-architecture.md)
- [API contract](api/openapi.yaml)
- [Data model](data-model.md)
- [Mobile UX architecture](mobile-ux-architecture.md)
- [Build roadmap](roadmap.md)

## Implementation Slices

- [Slice 001: Gateway foundation](implementation/slice-001-gateway-foundation.md)

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

## Team Boundaries

- Hermes-side gateway team: system architecture, API contract, approval framework, data model, threat model.
- Mobile backend services team: gateway service boundaries, auth, events, push, audit, inventory, voice coordinator.
- iOS team: mobile UX architecture, API contract, auth design, push framework, voice phases.
- Android team: same mobile contracts with Android secure storage and notification behavior.
- Push team: push framework, threat model, audit and rate-limit requirements.
- Approval/intervention team: approval framework, auth design, data model, ADRs.
- Voice team: voice architecture, API voice endpoints, roadmap phase 6.
- Multi-agent team: inventory schema, event stream, dashboard and grouping requirements.
