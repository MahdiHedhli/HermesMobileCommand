# Implementation Slice 001: Gateway Foundation

## Scope

This slice creates the first executable vertical foundation for Hermes Mobile Control Plane.

Included:

- Hermes Control Gateway skeleton under `gateway/`
- Device pairing endpoints
- Local SQLite persistence
- Device public-key registration model
- Approval queue skeleton
- `mobile_notify` endpoint
- Local append-only audit records
- Persisted event envelopes and WebSocket streaming
- Flutter-compatible mobile application shell under `mobile/`

Excluded:

- APNs and FCM dispatch
- Cloud relay
- Public internet exposure
- Voice implementation
- Browser intervention implementation
- Agent execution or multi-agent orchestration

## Architecture Decisions

- Gateway stack: Python FastAPI.
- Storage: SQLite local database, documented in [ADR-0010](../adr/0010-sqlite-local-gateway-storage-for-first-slice.md).
- API prefix: `/v1`.
- Pairing endpoints: `POST /v1/pairing/start` plus `POST /v1/pairing/sessions` alias.
- Event transport: WebSocket at `/v1/events/stream`, with REST backfill at `/v1/events`.
- Push provider behavior: `mobile_notify` persists notification and audit records but does not dispatch to APNs or FCM.
- Approval behavior: decisions fail closed if approval state is not pending, expired, device is inactive, or required signature metadata is missing.

## Validation

Run:

```bash
uv run --project gateway pytest
uv run --project gateway ruff check
uv run --project gateway python -m compileall src tests
```

Flutter validation requires Flutter SDK availability:

```bash
flutter analyze mobile
```
