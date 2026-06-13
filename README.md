# Agentic Control Tower

The control tower for agentic actions. Grant, deny, audit.

Agentic Control Tower, or ACT, is a self-hosted, Tailscale-first operator
surface for agentic backends. It lets an operator see consequential work,
receive urgent notices, grant or deny clearances from a phone, and keep an
auditable record without exposing a backend to the public internet.

## Control Tower Model

A control tower does not fly the planes.

It:

- grants clearances
- denies clearances
- sequences traffic
- keeps the log
- tracks state
- enforces procedure

The aircraft do the flying. In ACT, backends, runtimes, and agents are the
aircraft. The operator phone is the controller headset. Runtime adapters
translate backend-specific requests into tower clearances. ACT authorizes
consequential actions; it does not execute those actions.

## What ACT Does

- Pairs trusted operator devices with a self-hosted gateway.
- Verifies signed mobile requests for sensitive decisions.
- Receives backend notices and turns them into durable notifications.
- Maintains clearance queues for consequential actions.
- Supports modified responses, constraints, and policy proposals.
- Streams live backend events to mobile clients.
- Records audit events for auth, clearance, notification, and handoff paths.
- Provides handoff modes for operator guidance, terminal prototype work,
  browser assistance, and text-backed voice interaction.

## What ACT Does Not Do

- It does not run the backend action.
- It does not replace backend policy or runtime internals.
- It does not require public exposure for self-hosted operation.
- It does not make push notifications the source of truth.
- It does not make Hermes the platform boundary.

## Hermes Adapter

Hermes remains adapter #1. Existing Hermes-specific implementation names,
adapter paths, and compatibility endpoints stay in place where they describe
real Hermes integration. The generic control-tower boundary is the
`RuntimeAdapter` protocol; Hermes sits behind it as the first concrete runtime
adapter.

Future consumers can mirror the same boundary without adopting Hermes concepts:

- AgenticKVM
- BrowserBridge
- other local or self-hosted agent backends

## Current Status

This is an active alpha foundation. The gateway and mobile app prove signed
clearances, runtime notices, event streaming, handoffs, and local smoke tests.
The current real-Hermes work has discovered installed desktop integration
points, but the next hard milestone is still one real backend action blocked on
one real phone clearance.

Security posture today:

- self-hosted first
- Tailscale/local-network first
- paired device identities
- Ed25519 signed sensitive requests
- explicit clearance channel policy
- allowlist-composed notification text
- fail-closed clearance behavior
- local audit logging
- dangerous development features disabled by default

## Repository Layout

- `gateway/`: ACT gateway service, RuntimeAdapter seam, Hermes adapter, tests,
  and smoke scripts.
- `mobile/`: Flutter operator headset alpha application.
- `docs/`: architecture, security, API, implementation, QA, roadmap, and
  adoption documentation.
- `specs/`: Spec Kit feature specifications.
- `examples/`: Hermes-compatible demo runtime workflow.

## Key Docs

- [Docs index](docs/README.md)
- [System architecture](docs/architecture/system-architecture.md)
- [API contract](docs/api/openapi.yaml)
- [Runtime client integration](docs/implementation/real-hermes-client-008.md)
- [Security threat model](docs/security/threat-model.md)
- [Clearance channel policy](docs/security/clearance-channel-policy.md)
- [Runtime security review](docs/security/runtime-integration-review.md)
- [Roadmap](docs/roadmap-next.md)

## Developer Quick Start

Gateway:

```bash
uv run --project gateway pytest gateway/tests
uv run --project gateway ruff check gateway/src gateway/tests gateway/scripts examples
uv run --project gateway python gateway/scripts/runtime_integration_smoke.py
uv run --project gateway python gateway/scripts/hermes_runtime_e2e.py
```

Mobile:

```bash
cd mobile
flutter pub get
flutter analyze
flutter test
```

Run the gateway locally:

```bash
uv run --project gateway uvicorn hermes_gateway.app:create_app --factory --reload
```
