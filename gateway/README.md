# Hermes Mobile Gateway

First executable vertical slice for Hermes Mobile Control Plane.

This service is intentionally self-hosted and local-first:

- FastAPI gateway skeleton
- SQLite local persistence
- Device pairing with expiring pairing tokens
- Device public-key registration model
- WebSocket event stream with persisted cursor backfill
- `mobile_notify` endpoint with durable notification and audit records
- Fail-closed approval decision skeleton

Run locally:

```bash
uv run --project gateway uvicorn hermes_gateway.app:create_app --factory --reload
```

Run tests:

```bash
uv run --project gateway pytest
uv run --project gateway ruff check
```

The default bind should remain local or private-network only. Do not expose this
gateway on the public internet.
