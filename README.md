# Hermes Mobile Control Plane

Hermes Mobile Control Plane is a self-hosted, Tailscale-first mobile operator platform for Hermes Agent installs. It focuses on secure mobile visibility, signed approvals, operator intervention, notifications, and runtime handoffs without requiring public exposure of a Hermes node.

## What Exists

- FastAPI Hermes Gateway sidecar with SQLite persistence.
- Device pairing and Ed25519 signed mobile requests.
- Approval lifecycle with modified responses and policy proposals.
- Hermes-facing runtime adapter and reusable Python runtime client.
- Demo runtime agent proving notification, approval, TUA, browser assistance, voice, and mission completion loops.
- Flutter mobile alpha with gateway-backed approvals, events, missions, notifications, agents, TUI/TUA, browser assistance, and text-backed voice surfaces.
- Local E2E smoke scripts and architecture/security documentation.

## Repository Layout

- `gateway/`: Hermes Gateway service, runtime adapter/client, tests, and smoke scripts.
- `mobile/`: Flutter mobile alpha application.
- `docs/`: architecture, security, API, implementation, QA, roadmap, and adoption documentation.
- `specs/`: Spec Kit feature specifications.
- `examples/`: Hermes-compatible demo runtime workflow.

## Key Docs

- [Docs index](docs/README.md)
- [API contract](docs/api/openapi.yaml)
- [Runtime client integration](docs/implementation/real-hermes-client-008.md)
- [Security threat model](docs/security/threat-model.md)
- [Runtime security review](docs/security/runtime-integration-review.md)
- [Platform roadmap](docs/roadmap-next.md)

## Local Validation

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

## Status

This is an active alpha foundation. It is not production-hardened, and dangerous operator capabilities remain gated by signed-device controls, local binding controls, and explicit development flags where applicable.
