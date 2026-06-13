# Real Hermes Client Integration 008

Sprint: `HERMES-MCP-REAL-HERMES-CLIENT-008`

## Purpose

This slice replaces the purely simulated runtime loop with a real Hermes-facing client path. The gateway remains decoupled from Hermes internals, but a Hermes-compatible process can now use a reusable Python client to request operator actions, block for results, and resume work from mobile decisions.

## What Is Real

- `gateway/src/hermes_gateway/runtime_client.py` provides `HermesRuntimeClient`.
- The client defaults to loopback gateway URLs and requires explicit opt-in for non-loopback URLs.
- The client supports retries, timeouts, typed result objects, and transport injection for tests.
- `examples/demo_runtime_agent.py` acts as a Hermes-compatible runtime wrapper using the same client a real Hermes integration would use.
- `gateway/scripts/hermes_runtime_e2e.py` runs the demo agent against an in-process gateway and resolves actions through signed mobile-compatible requests.
- Runtime-created missions are exposed to mobile through `GET /v1/missions` and `GET /v1/missions/{mission_id}`.
- Flutter gateway repositories can read mission records and show mission state badges.

## Runtime Client API

Primary methods:

- `register_context(...)`
- `notify(...)`
- `request_approval(...)`
- `approval(...)`
- `wait_for_approval(...)`
- `request_assistance(...)`
- `request_browser_assistance(...)`
- `request_voice(...)`
- `fetch_operator_session(...)`

Result models:

- `NotificationResult`
- `ApprovalDecision`
- `AssistanceResult`
- `BrowserAssistanceResult`
- `VoiceInteractionResult`

The blocking helpers poll loopback runtime result endpoints. They return when a terminal or operator-actionable state is reached. For approvals, `modified`, `needs_info`, and `propose_policy` are treated as delivered runtime results even if the approval remains pending.

## Demo Workflow

The demo runtime agent:

1. Registers agent, session, and mission context.
2. Sends a mobile notification.
3. Enters `waiting_approval`.
4. Requests a shell approval and blocks until mobile approves.
5. Requests a second approval and blocks until mobile returns a modified directive with constraints.
6. Enters `waiting_assistance`.
7. Requests TUA and blocks until the operator returns a summary.
8. Enters `user_controlling`.
9. Requests browser assistance and blocks until the operator returns a summary.
10. Requests a text-backed voice interaction and blocks until the session closes.
11. Marks the mission and agent completed.

## Mission Lifecycle

Mission states now align with runtime-facing operator states:

- `queued`
- `running`
- `waiting_approval`
- `waiting_assistance`
- `user_controlling`
- `completed`
- `failed`
- `cancelled`

The gateway stores mission records from runtime context registration, emits `mission.state` events, and exposes the mission read model to signed mobile clients. Full mission CRUD, history, ownership transfer, and mission timelines remain future work.

## Approval Lifecycle

The runtime client can request and wait for:

- `approve_once`
- `approve_session`
- `approve_agent`
- `deny`
- `modified`
- `needs_info`
- `propose_policy`

Mobile decisions still require Ed25519 signed paired-device requests. The runtime client never signs mobile decisions and never bypasses approval policy.

## Operator Session Lifecycle

TUA, browser assistance, and voice still use their subtype-specific routes and security checks. The shared `OperatorSession` projection gives runtime and mobile surfaces a common way to discover active handoffs without collapsing subtype boundaries.

## QA Results

See [runtime integration QA](../qa/runtime-integration-qa.md).

## Security Review

See [runtime integration security review](../security/runtime-integration-review.md).

## Known Limitations

- This is a Hermes-compatible demo wrapper, not a patched Hermes core runtime.
- Runtime result delivery is polling over local HTTP.
- Browser assistance has notes and return-control only; no browser streaming.
- Voice is text-backed only; no STT, TTS, audio capture, or WebRTC.
- Mission timelines and mission management UX are still thin.
- Native mobile validation remains Chrome-first in this development environment.
