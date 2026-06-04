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
- Hermes tool adapter with loopback-first binding controls

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

Hermes-local tool calls should use loopback by default:

```python
from hermes_gateway.hermes_adapter import HermesToolAdapter

adapter = HermesToolAdapter(gateway_base_url="http://127.0.0.1:8787/v1")
```

If Hermes and the gateway are intentionally split across private infrastructure,
set `HERMES_ALLOWED_HERMES_CALLERS` or `HERMES_GATEWAY_ALLOWED_HERMES_CALLERS`
to exact allowed caller addresses.

Run the E2E smoke path:

```bash
uv run --project gateway python gateway/scripts/e2e_smoke.py
```
