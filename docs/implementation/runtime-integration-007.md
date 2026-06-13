# Runtime Integration 007

Sprint: `HERMES-MCP-RUNTIME-INTEGRATION-007`

## Purpose

This slice replaces gateway-only assumptions with a runtime adapter boundary. The gateway can now accept local Hermes runtime requests, create durable mobile-facing records, and expose runtime-readable results after signed mobile actions.

The implementation remains self-hosted first, Tailscale first, and loopback-only for runtime calls by default.

## What Is Real

Runtime-facing API:

- `POST /v1/runtime/context`
- `POST /v1/runtime/notifications`
- `POST /v1/runtime/approvals`
- `GET /v1/runtime/approvals/{approval_id}/result`
- `POST /v1/runtime/approvals/{approval_id}/cancel`
- `POST /v1/runtime/tua/requests`
- `GET /v1/runtime/tua/requests/{request_id}/result`
- `POST /v1/runtime/browser-assistance/sessions`
- `GET /v1/runtime/browser-assistance/sessions/{session_id}/result`
- `POST /v1/runtime/voice/sessions`
- `GET /v1/runtime/voice/sessions/{session_id}/result`

Gateway records:

- Runtime context can upsert Agent, Session, and Mission projections.
- Runtime approvals become normal pending Approval records.
- Signed mobile approval decisions are visible through runtime result polling.
- Modified approval responses and constraints are visible to runtime.
- TUA return-control summaries are visible to runtime.
- Browser assistance return-control summaries are visible to runtime.
- Text-backed voice messages and close state are visible to runtime.
- OperatorSession projection records are created for TUI, TUA, browser assistance, and voice paths.
- Capability checks are centralized for runtime-created operator sessions and signed mobile actions.

Smoke coverage:

- `gateway/scripts/runtime_integration_smoke.py` simulates a Hermes runtime and paired mobile device using a temporary SQLite database.

## What Is Simulated

- No external Hermes process is launched.
- No APNs or FCM push provider is used.
- Browser assistance is note and return-control only; no browser stream or remote control exists.
- Voice is text-backed only; no audio, STT, TTS, or WebRTC exists.
- Runtime result delivery is polling over loopback HTTP, not callback/webhook delivery.
- Capability grants are enforced through the centralized helper and agent/node capability metadata; grant management UX is not built.

## Adapter Boundary

The runtime boundary lives in `gateway/src/hermes_gateway/runtime_adapter.py`.

Responsibilities:

- Translate local runtime requests into gateway records.
- Emit gateway events for mobile clients.
- Append audit events for runtime-created control-plane records.
- Maintain runtime-facing result views.
- Keep Hermes-specific calls out of mobile routes.

The gateway does not import Hermes runtime internals. A future runtime can integrate through local HTTP, a Python client wrapper, or tool-shaped calls that target these endpoints.

## Runtime Calling Pattern

1. Hermes identifies active work:

   ```http
   POST /v1/runtime/context
   ```

2. Hermes requests mobile attention or approval:

   ```http
   POST /v1/runtime/notifications
   POST /v1/runtime/approvals
   ```

3. Mobile user acts through signed mobile APIs:

   ```http
   POST /v1/approvals/{approval_id}/approve_once
   POST /v1/approvals/{approval_id}/responses
   POST /v1/tua/sessions/{session_id}/return-control
   POST /v1/browser-assistance/sessions/{session_id}/return-control
   POST /v1/voice/sessions/{session_id}/messages
   ```

4. Hermes polls result endpoints:

   ```http
   GET /v1/runtime/approvals/{approval_id}/result
   GET /v1/runtime/tua/requests/{request_id}/result
   GET /v1/runtime/browser-assistance/sessions/{session_id}/result
   GET /v1/runtime/voice/sessions/{session_id}/result
   ```

## Security Boundaries

- Runtime endpoints use the same loopback and explicit caller allowlist controls as previous Hermes-local endpoints.
- Non-loopback runtime calls are rejected unless configured through `HERMES_ALLOWED_HERMES_CALLERS` or `HERMES_GATEWAY_ALLOWED_HERMES_CALLERS`.
- Rejected local runtime calls are audited without logging secrets.
- Sensitive mobile decisions still require Ed25519 signed paired-device requests.
- Runtime-created TUA, browser assistance, and voice sessions require central capability checks.
- TUI remains development-only unless explicitly enabled.
- Permanent policy activation is still not implemented by approval policy proposals.

## Runtime State Model

Agent states now include:

- `idle`
- `running`
- `blocked`
- `waiting_approval`
- `waiting_assistance`
- `user_controlling`
- `paused`
- `failed`
- `completed`

Mission states now include:

- `queued`
- `running`
- `waiting_approval`
- `waiting_assistance`
- `user_controlling`
- `completed`
- `failed`
- `cancelled`

Runtime context registration emits `agent.status` and `mission.state` events.

## OperatorSession Status

`operator_sessions` is a projection layer, not a replacement for subtype tables.

Implemented:

- Common fields for session ID, type, agent, mission, state, owner device, capability requirements, context, and return summary.
- TUI, TUA, browser assistance, and voice creation/update hooks.
- Signed mobile list endpoint: `GET /v1/operator-sessions`.

Not implemented:

- Full storage normalization.
- Unified route handlers.
- Cross-session analytics.

## CapabilityGrant Status

Implemented:

- `capability_grants` storage table.
- Central runtime/device capability helper.
- Audit event `capability_check_denied`.
- Runtime-created TUA, browser assistance, and voice checks.
- Mobile approval, TUI, TUA, browser assistance, and voice checks routed through the helper.

Not implemented:

- Mobile UX for grant management.
- Durable grant review workflow.
- Active permanent policy enforcement.

## Smoke Result

`gateway/scripts/runtime_integration_smoke.py` verifies:

1. Runtime context registration.
2. Runtime notification creation.
3. Runtime approval request.
4. Signed mobile approval.
5. Runtime approval result polling.
6. Modified approval response with constraint.
7. Runtime modified result polling.
8. TUA request, message, return-control summary.
9. Browser assistance notes and return-control summary.
10. Runtime-created text-backed voice session, mobile message, close state.
11. Event records exist.
12. Audit records exist.

## Remaining Before Real Hermes Process Integration

- Integrate the `HermesRuntimeClient` wrapper into actual Hermes tool policy.
- Replace polling with optional callback delivery where blocking wait helpers are not sufficient.
- Map real Hermes task/session identifiers into durable Mission IDs in Hermes core.
- Feed real Hermes live activity into `agent.status`, `agent.activity`, and `mission.state`.
- Add runtime cancellation semantics for TUA, browser assistance, and voice.
- Complete native iOS/Android validation of signed mobile decisions.
- Add operator UX for CapabilityGrant review and revocation.
