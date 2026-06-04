# Hermes Wingman Backend/API Lessons

## Purpose

This document captures backend lessons from hermes-wingman's Rust Axum backend and Rails web proxy for use in Hermes Mobile Control Plane.

## Inspected Backend Surfaces

- `backend/openapi.yaml`
- `backend/src/main.rs`
- `backend/src/handlers/*`
- `backend/src/platform.rs`
- `backend/src/helpers.rs`
- `backend/src/models.rs`
- `web/config/routes.rb`
- `web/app/services/hermes_api_service.rb`
- `web/app/controllers/*`

## Endpoint Categories Worth Mirroring

Mirror the concept, not the exact security model.

| Wingman Endpoint(s) | Purpose | HermesMobileCommand Mapping |
| --- | --- | --- |
| `GET /health` | Backend/Hermes health | `GET /health`, node health snapshots |
| `GET /sessions` | Session list | `GET /sessions` with `node_id`, `agent_id`, status filters |
| `GET /logs` | Log entries by level/lines | Event stream plus `GET /sessions/{id}/activity`; redacted log tail |
| `GET /models` | Model/capability status | Optional read-only agent/model capability metadata |
| `GET /hermes/skills` | Skills list | Read-only skills/memory visibility in node/agent detail |
| `GET /memory`, `POST /memory/search` | Memory read/search | Redacted memory visibility; mutation approval-gated |
| `GET /gateway`, `GET /gateway/platforms` | Gateway status/platforms | Node/gateway health and capability registry |
| `GET /cron` | Scheduled tasks | Agent scheduled-task visibility |
| `GET /metrics` | Backend metrics | Gateway diagnostics and health metadata |

## Endpoints To Avoid Directly

| Wingman Endpoint(s) | Reason To Avoid | Replacement |
| --- | --- | --- |
| `POST /config/write`, `POST /config/update` | Raw mobile config mutation is out of scope and unsafe | Read-only redacted config summary; signed approval for targeted changes later |
| `PUT /files/write`, `POST /files/delete`, `POST /files/rename`, `POST /files/mkdir` | Direct filesystem mutation, broad path access | Session artifact viewer; approval-gated file actions |
| `GET /files/read` as broad file reader | Can expose arbitrary sensitive local files in inspected backend | Redacted/scoped artifact reads only |
| `POST /hermes/command` | Generic CLI proxy | Explicit allowlisted gateway endpoints |
| `/cli/*` wrappers | Exposes debug, dump, secrets, backup, plugins, security outputs | Safe diagnostics endpoints with redaction and audit |
| `POST /auth/api-key`, `POST /auth/login/{provider}` | Provider auth belongs to Hermes/admin surfaces, not mobile control plane MVP | Device pairing/auth only |
| `POST /setup/install`, `POST /setup/auto-configure` | Remote/mobile installation and config writes are outside scope | Local gateway installer/admin docs |
| `POST /gateway/configure/{platform}` | Writes secrets into `.env` from mobile-accessible API | Future secret-safe local admin flow |
| `POST /gateway/toggle`, `POST /gateway/service/{action}` | Service controls need signed intervention and audit | Intervention API: pause, kill task, kill agent, quarantine |
| `GET /chat/stream?message=...` | GET query can leak user message in logs/URLs | POST message plus WebSocket event stream |

## Data Models Worth Adapting

| Wingman Model / Source | Usefulness | Required Changes |
| --- | --- | --- |
| `HermesSession` | Good base for session list UX | Add `node_id`, `agent_id`, `conversation_id`, `status`, current plan/tool/target, approval counts |
| `HermesStatus` | Good node/agent status concept | Split into NodeHealth and AgentHealth |
| `LogEntry` | Useful log parsing/display | Add redaction state, event cursor, source, node/agent/session scope |
| `SkillEntry` | Useful skills visibility | Add capability status and policy mutation requirements |
| `MemoryEntry` | Useful memory search/list | Add redaction, sensitivity labels, approval-gated deletion |
| `GatewayPlatform` | Useful connected platform status | Add node scope, platform capability, health, last error redaction |
| Rails `Mission` | Useful task/mission vocabulary | Convert to session/task entity; no direct local run behavior |
| Rails `Profile` | Useful preset concept later | Defer; applying presets is consequential config mutation |
| Rails `UsageSnapshot` | Useful analytics idea | Not MVP; possible local diagnostics later |

## Missing Endpoints We Need

Hermes Wingman does not provide the key control-plane endpoints HermesMobileCommand needs:

| Needed Endpoint Family | Required For |
| --- | --- |
| Pairing sessions | New mobile app trust establishment |
| Device registry and revocation | Lost/compromised phone handling |
| Token refresh with device proof | Mobile auth lifecycle |
| Approval queue | Pending risky actions |
| Signed approval decisions | Safe approve/deny |
| Emergency interventions | Pause, kill task, kill agent, quarantine |
| Push notification requests and records | `mobile_notify`, delivery audit, dedupe |
| WebSocket event stream with cursor | Live activity and reconnect/backfill |
| Multi-node inventory | Tailscale-first many-node control plane |
| Audit event query/export | Forensic review |
| Voice sessions/turns | Push-to-talk and future WebRTC |

These are already represented in [our OpenAPI contract](../api/openapi.yaml).

## Approval Queue Differences

Wingman:

- No observed signed approval model.
- High-risk actions are ordinary GUI endpoints.
- Service stop pipes confirmation into CLI internally.

HermesMobileCommand:

- Gateway approval engine is mandatory.
- Risk levels: low, medium, high, critical.
- States: pending, approved, denied, expired, cancelled.
- Scopes: once, session, agent, permanent.
- Signed decisions bind action, node, agent, session, scope, payload hash, and expiry.
- Emergency controls are signed and audited.

## Push Notification Differences

Wingman:

- No push notification framework observed in inspected backend.
- Mobile discovery depends on LAN scanning/manual host entry.

HermesMobileCommand:

- `mobile_notify` is a first-class gateway tool.
- Notifications are categorized: `approval_required`, `security_alert`, `agent_blocked`, `task_complete`, `system_health`, `voice_callback`.
- Push payloads are secret-free hints.
- Durable state remains in gateway.
- Rate limit, dedupe, and audit are required.

## Event Streaming Lessons

Wingman:

- Uses SSE chat stream.
- Logs screen polls periodically.
- Rails plan references Action Cable/Hotwire, but inspected gateway API is REST/SSE oriented.

HermesMobileCommand:

- WebSocket is primary live activity transport.
- REST backfill by cursor is required.
- SSE may remain a secondary read-only fallback.
- WebRTC is reserved for voice/browser/screen phases.

Lesson:

- Wingman's SSE streaming confirms that streaming UX is valuable, but our primary stream must include cursoring, node scope, event types, auth, redaction, and reconnect semantics.

## Auth/Security Lessons

Findings:

- No app-level auth middleware observed in Rust backend.
- `CorsLayer::permissive()` is used.
- Provider API keys can be passed to backend and CLI.
- `.env` secrets can be written through gateway configuration.
- File access can escape `~/.hermes`.
- Generic Hermes command proxy exists.

Required divergence:

- Device pairing and signed approvals are mandatory.
- Tailscale identity is not sufficient.
- No generic CLI or filesystem APIs.
- Every consequential action is policy-checked and audited.
- Push title/body secret filtering is required.

## Build/Test Lessons

Useful:

- CI intent includes Rust formatting, Clippy, Flutter analyze, Flutter builds, Rails Brakeman/RuboCop.
- Build scripts show cross-platform packaging considerations.

Cautions:

- CI paths appear inconsistent with inspected `web/` directory because workflow references `hermes_wingman_web`.
- Tests are shallow smoke/fixture tests.
- No security tests for auth, file access, secret redaction, or command execution were found.

Recommendation:

- Use the CI categories as inspiration, but build project-specific checks for OpenAPI, docs, gateway auth, approval replay, redaction, and mobile integration.
