# Implementation Slice 003: Hermes Integration And Mobile Readiness

## Scope

This slice connects the secure gateway foundation to Hermes-facing tools and gives the mobile shell a concrete data-layer architecture.

Included:

- Hermes tool adapter module under `gateway/src/hermes_gateway/hermes_adapter.py`
- Tool-shaped Hermes endpoints:
  - `POST /v1/hermes/tools/mobile_notify`
  - `POST /v1/hermes/tools/approval_requested`
  - `POST /v1/hermes/tools/approval_status`
- Loopback-first binding controls for Hermes-local write/tool endpoints
- Signed mobile-readable inventory, agent, session, approval, notification, audit, and event APIs
- Approval status metadata for Hermes polling after a signed mobile decision
- Flutter data-layer skeleton with API client, signing abstraction, secure storage abstraction, models, repositories, and event-stream stub
- Local E2E smoke script under `gateway/scripts/e2e_smoke.py`

Excluded:

- APNs and FCM dispatch
- Real Hermes process integration
- Public relay
- Voice implementation
- Browser intervention implementation
- Mobile Ed25519 private-key storage implementation

## Hermes Tool Adapter

Hermes can use the Python adapter:

```python
from hermes_gateway.hermes_adapter import HermesToolAdapter

adapter = HermesToolAdapter(gateway_base_url="http://127.0.0.1:8787/v1")
notification = adapter.mobile_notify(
    title="Approval required",
    body="Hermes needs a mobile decision.",
    urgency="high",
    category="approval_required",
    agent_id="agent_mock",
    session_id="sess_mock",
    action_id="act_123",
)
approval = adapter.approval_requested(
    requested_tool="shell",
    risk_level="high",
    summary="Run a redacted shell command.",
    payload_redacted={"command": "redacted"},
    agent_id="agent_mock",
    session_id="sess_mock",
    expires_in_seconds=300,
    suggested_scopes=["once"],
)
status = adapter.approval_status(approval_id=approval["approval_id"])
```

The adapter talks to the gateway on loopback by default. It does not send APNs or FCM pushes. Notification and approval records are persisted by the gateway, audited locally, and emitted as event envelopes.

## Local Binding Controls

Hermes-local endpoints reject non-loopback callers unless the caller address is configured in `HERMES_ALLOWED_HERMES_CALLERS` or `HERMES_GATEWAY_ALLOWED_HERMES_CALLERS`.

Default allowed callers:

- `127.0.0.1`
- `::1`
- `localhost`

Explicit allowlist example:

```bash
HERMES_ALLOWED_HERMES_CALLERS=100.64.12.34,192.168.1.50
```

Operating modes:

- Loopback mode: Hermes and the gateway run on the same host. Hermes calls `http://127.0.0.1:8787/v1`.
- Tailscale mode: mobile devices reach the gateway through the node's Tailscale address, while Hermes-local tool calls still prefer loopback.
- Allowlisted private caller mode: if Hermes is separated from the gateway on a private network, the gateway may allow that specific private/Tailscale source address.

Rejected Hermes-local calls create `hermes_local_request_rejected` audit events with the caller address hashed.

## Route Protection Matrix

| Route | Caller | Protection |
| --- | --- | --- |
| `POST /v1/pairing/start` | local operator or mobile bootstrap | unauthenticated pairing bootstrap |
| `POST /v1/pairing/complete` | mobile bootstrap | pairing token |
| `POST /v1/nodes/register` | Hermes-local | loopback or allowlisted caller |
| `POST /v1/notifications/mobile_notify` | Hermes-local | loopback or allowlisted caller |
| `POST /v1/hermes/tools/mobile_notify` | Hermes-local | loopback or allowlisted caller |
| `POST /v1/approvals` | Hermes-local | loopback or allowlisted caller |
| `POST /v1/hermes/tools/approval_requested` | Hermes-local | loopback or allowlisted caller |
| `POST /v1/hermes/tools/approval_status` | Hermes-local | loopback or allowlisted caller |
| `GET /v1/inventory` | mobile | signed device request |
| `GET /v1/nodes/{node_id}` | mobile | signed device request |
| `GET /v1/agents` | mobile | signed device request |
| `GET /v1/agents/{agent_id}` | mobile | signed device request |
| `GET /v1/sessions` | mobile | signed device request |
| `GET /v1/sessions/{session_id}` | mobile | signed device request |
| `GET /v1/sessions/{session_id}/activity` | mobile | signed device request |
| `GET /v1/approvals` | mobile | signed device request |
| `GET /v1/approvals/{approval_id}` | mobile | signed device request |
| `POST /v1/approvals/{approval_id}/approve_once` | mobile | signed device request |
| `POST /v1/approvals/{approval_id}/deny` | mobile | signed device request |
| `GET /v1/notifications` | mobile | signed device request |
| `GET /v1/events` | mobile | signed device request |
| `GET /v1/audit/events` | mobile | signed device request |
| `GET /v1/events/stream` | mobile | paired device access token |

## Tool Behaviors

### `mobile_notify`

Accepted fields:

- `title`
- `body`
- `urgency`
- `category`
- `agent_id`
- `session_id`
- optional `action_id`
- optional `deep_link`

Policy:

- Title maximum: 120 characters.
- Body maximum: 800 characters.
- Secret-looking title/body text is rejected.
- Accepted notifications create `notification_queued` audit records.
- Accepted notifications emit `notification.created`.
- Rejected notifications create `notification_rejected`.

### `approval_requested`

Accepted fields:

- `requested_tool`
- `risk_level`
- `summary`
- `payload_redacted`
- `agent_id`
- `session_id`
- `expires_in_seconds`
- optional `suggested_scopes`
- optional `action_id`

Behavior:

- Creates a pending approval request.
- Converts suggested scopes into approval options.
- Emits `approval.requested`.
- Audits `approval_requested`.
- Never auto-approves.

### `approval_status`

Accepted fields:

- `approval_id`

Behavior:

- Returns current state.
- Returns selected scope only when the approval is approved.
- Returns decision timestamp and non-secret decision metadata.
- Rejects unknown approval IDs with `404`.

## Mobile Data Layer

The Flutter skeleton now contains:

- `GatewayConfig`: base URL resolution under `/v1`.
- `GatewayApiClient`: JSON GET/POST client with signed request hooks.
- `DeviceRequestSigner`: interface for canonical request signing.
- `SecureKeyStore`: placeholder abstraction for iOS Keychain and Android Keystore integration.
- Models for nodes, agents, approvals, notifications, events, and dashboard snapshots.
- Repositories for dashboard, agents, approvals, notifications, and event backfill.
- `GatewayEventStreamClient`: stream client stub reserved for WebSocket token/reconnect policy.

The mobile app does not yet implement Ed25519 signing or secure key persistence. The current data layer establishes where those implementations attach.

## E2E Smoke

Run:

```bash
uv run --project gateway python gateway/scripts/e2e_smoke.py
```

The script:

1. Starts a gateway on `127.0.0.1` with a temporary SQLite database.
2. Registers a local Hermes node.
3. Pairs a generated Ed25519 test device.
4. Calls `mobile_notify` through the adapter.
5. Calls `approval_requested` through the adapter.
6. Lists pending approvals as a signed mobile request.
7. Approves the approval using signed mobile headers.
8. Calls `approval_status` through the adapter.
9. Verifies event and audit records exist.

The script does not require APNs, FCM, real Hermes, a mobile device, or public network access.

## Validation

Required checks:

```bash
uv run --project gateway pytest gateway/tests
uv run --project gateway ruff check gateway/src gateway/tests
uv run --project gateway python -m compileall gateway/src gateway/tests
uv run --project gateway python gateway/scripts/e2e_smoke.py
uvx --from git+https://github.com/github/spec-kit.git specify check
```

Flutter checks should run only when Flutter SDK is available.
