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

## Slice 002 Secure Pairing And Approvals

### Device Request Signing

Sensitive mobile control requests use Ed25519 signatures from the device key registered during pairing.

Required headers:

- `X-HMCP-Device-Id`
- `X-HMCP-Timestamp`
- `X-HMCP-Nonce`
- `X-HMCP-Signature`

Canonical string:

```text
HMCP-SIGN-V1
METHOD
/v1/path?query
unix_timestamp_seconds
nonce
sha256(raw_request_body)
```

Rules:

- Timestamp tolerance is 300 seconds.
- Nonces are unique per device and persisted in SQLite.
- Unknown, revoked, stale, replayed, path-tampered, method-tampered, and body-tampered requests fail closed.
- Failed auth attempts create `auth_signature_failed` audit events without storing body or signature values.

### Route Protection Matrix

| Route | Protection | Notes |
| --- | --- | --- |
| `POST /v1/pairing/start` | unauthenticated bootstrap | Local operator pairing ceremony |
| `POST /v1/pairing/complete` | pairing token | Registers device public key |
| `GET /v1/devices` | signed device request | Device management |
| `DELETE /v1/devices/{device_id}` | signed device request | Revokes device and tokens |
| `POST /v1/approvals` | Hermes-local | Creates pending approval request |
| `GET /v1/approvals` | signed device request | Mobile approval queue |
| `GET /v1/approvals/{approval_id}` | signed device request | Approval detail |
| `POST /v1/approvals/{approval_id}/decisions` | signed device request | Generic approve/deny |
| `POST /v1/approvals/{approval_id}/approve_once` | signed device request | Convenience approval |
| `POST /v1/approvals/{approval_id}/deny` | signed device request | Convenience denial |
| `POST /v1/approvals/{approval_id}/expire` | signed device request | Manual expiry |
| `POST /v1/approvals/{approval_id}/cancel` | signed device request | Manual cancel |
| `POST /v1/notifications/mobile_notify` | Hermes-local | Provider dispatch still out of scope |
| `GET /v1/notifications` | signed device request | Notification history |
| `GET /v1/audit/events` | signed device request | Audit history |
| `GET /v1/events/stream` | paired device access token | WebSocket stream |
| `POST /v1/sessions/{session_id}/interventions` | signed device request | Placeholder only; does not execute intervention |

### Approval Lifecycle Example

Create an approval request:

```http
POST /v1/approvals
```

```json
{
  "action_id": "act_123",
  "agent_id": "agent_mock",
  "session_id": "sess_mock",
  "requested_tool": "shell",
  "risk_level": "high",
  "summary": "Run a command",
  "full_payload_redacted": {"command": "redacted"},
  "resource_scope": "repo",
  "expires_at": "2099-01-01T00:00:00Z"
}
```

Approve once with signed headers:

```http
POST /v1/approvals/{approval_id}/approve_once
X-HMCP-Device-Id: dev_...
X-HMCP-Timestamp: 1798761600
X-HMCP-Nonce: nonce_...
X-HMCP-Signature: ...
```

Terminal states are `approved`, `denied`, `expired`, and `cancelled`. Any terminal approval rejects later transitions.
