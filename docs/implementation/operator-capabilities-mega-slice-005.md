# Operator Capabilities Mega Slice 005

Sprint: `HERMES-MCP-OPERATOR-CAPABILITIES-MEGA-SLICE-005`

## Summary

This slice adds thin, working operator-capability paths across the gateway and
mobile app. The focus is integration and smoke coverage, not deep production
hardening.

Implemented capabilities:

- TUI follow-up hardening with signed attach tokens, per-device `tui`
  permission, per-agent or per-node `tui` capability checks, paste risk
  metadata, output-retention flag, and clearer terminal risk labels.
- TUA backend requests, sessions, user messages, return-control, close, audit,
  and events.
- Browser assistance sessions with operator notes, return-control, close, audit,
  and events. No browser stream is implemented.
- Advanced approval responses for `modified`, `needs_info`, `approve_once`,
  `approve_session`, `approve_agent`, `deny`, and proposal-only
  `propose_policy`.
- Platform-aware mobile secure storage abstraction using native secure storage
  where available and explicit web/dev fallback elsewhere.
- Text-backed Voice MVP with signed voice sessions, messages, close, audit, and
  events. No streaming audio or external STT/TTS provider is implemented.

## Security Defaults

- Self-hosted and Tailscale-first assumptions remain unchanged.
- All mobile operator actions use signed paired-device requests.
- Hermes-local creation endpoints remain loopback/allowlist controlled.
- TUI PTY remains disabled by default and requires
  `HERMES_TUI_ENABLE_LOCAL_PTY=1`.
- TUI session creation requires device `tui` permission and agent or node `tui`
  capability.
- TUI WebSocket access requires a short-lived attach token minted through a
  signed device request.
- Terminal output retention is disabled by default.
- Approve Forever creates an `ApprovalPolicyProposal` only; it does not activate
  a permanent allow policy.

## Gateway APIs Added

- `POST /v1/tui/sessions/{session_id}/attach-token`
- `POST /v1/tua/requests`
- `GET /v1/tua/requests`
- `GET /v1/tua/requests/{request_id}`
- `POST /v1/tua/requests/{request_id}/sessions`
- `GET /v1/tua/sessions/{session_id}`
- `POST /v1/tua/sessions/{session_id}/messages`
- `POST /v1/tua/sessions/{session_id}/return-control`
- `POST /v1/tua/sessions/{session_id}/close`
- `POST /v1/browser-assistance/sessions`
- `GET /v1/browser-assistance/sessions`
- `GET /v1/browser-assistance/sessions/{session_id}`
- `POST /v1/browser-assistance/sessions/{session_id}/event`
- `POST /v1/browser-assistance/sessions/{session_id}/return-control`
- `POST /v1/browser-assistance/sessions/{session_id}/close`
- `POST /v1/approvals/{approval_id}/responses`
- `GET /v1/approvals/{approval_id}/policy-proposals`
- `POST /v1/voice/sessions`
- `GET /v1/voice/sessions/{session_id}`
- `POST /v1/voice/sessions/{session_id}/messages`
- `POST /v1/voice/sessions/{session_id}/close`

## Mobile Changes

- Pairing requests now ask for `tui`, `browser_assist`, and `voice` grants in
  addition to read, approval, and intervention grants.
- TUI creates an attach token before opening the WebSocket stream.
- TUA screen can use gateway-backed sessions where a matching request/session
  exists, with mock fallback.
- Approval More actions now submit modified responses, needs-info requests, and
  proposal-only Approve Forever responses when paired.
- Browser Assistance screen lists existing sessions and supports notes and
  return-control.
- Voice screen starts text-backed voice sessions, sends fallback messages, and
  closes sessions.
- Secure storage is platform-aware; web/dev fallback is shown explicitly in
  settings.

## E2E Smoke

`gateway/scripts/e2e_operator_capabilities_smoke.py` starts a temporary local
gateway and verifies:

1. Device pairing with operator permissions.
2. Mobile notification creation.
3. Approval request plus modified response with constraint.
4. TUA request/session/message/return-control.
5. Browser assistance session/note/return-control.
6. Voice session/message/close.
7. TUI session with capability grant and attach token.
8. Event and audit records exist for the flow.

The smoke requires no APNs, FCM, real Hermes, real browser, real native device,
or public network.

## Remaining Production Hardening

- Harden TUI execution with sandboxing or a dedicated terminal broker before
  production shell access.
- Add durable policy-review workflow before any permanent approval policy can be
  activated.
- Add true native secure-key validation on iOS/Android devices once native
  toolchains are fully installed.
- Add browser streaming/takeover protocol if Browser Assistance graduates beyond
  notes and summaries.
- Add live audio capture, STT/TTS provider adapters, and WebRTC only after the
  text-backed voice contract is stable.
- Add ownership checks for multi-user/multi-device enterprise scenarios.

## Validation

Validation for this slice covers gateway tests, Flutter tests, ruff, compileall,
OpenAPI YAML parse, docs scans, Spec Kit check, and the local mega-smoke script.
