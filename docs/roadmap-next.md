# ACT Roadmap

Sprint lineage: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`, reframed by
`ACT-002`.

This roadmap is intentionally narrow. Platform expansion ideas live in
[parking-lot.md](parking-lot.md) until ACT proves one real backend action can
block on one real phone clearance.

## Phase A: Native Validation And Production Hardening

Goal:

- Make the current tower reliable on native mobile targets and reduce security
  ambiguity.

Scope:

- Complete iOS and Android toolchain validation.
- Validate secure storage on iOS Keychain and Android Keystore.
- Harden signed clearance requests and device lifecycle behavior.
- Add first-class CapabilityGrant revocation UX.
- Keep TUI development-only unless explicitly enabled.
- Add endpoint maturity labels to OpenAPI.
- Harden WebSocket auth and attach-token patterns.

Exit criteria:

- iOS and Android app launches against a local ACT gateway.
- Signed clearance flow works on at least one iOS and one Android target.
- Gateway and Flutter validation pass on the beta branch.
- Existing Hermes adapter behavior remains intact.

## Phase B: Real Hermes Runtime Clearance

Goal:

- Move from local smoke paths to one real Hermes action blocked on one real
  phone clearance.

Scope:

- Build on the RuntimeAdapter seam and existing HermesRuntimeClient helpers.
- Wire `HermesRuntimeClient` into Hermes runtime/tool policy.
- Make notification, clearance, and return-control helpers consumable by
  blocked Hermes actions.
- Map Hermes-specific mission/session/task identifiers into ACT work-state
  projections without leaking those terms into the generic protocol.
- Feed real Hermes activity into Home, Agent Detail, Inbox, and audit views.

Exit criteria:

- A real Hermes action requests clearance, blocks, receives a signed mobile
  decision, and resumes or stops correctly.
- A real Hermes assistance request returns operator guidance to Hermes.
- ACT audit records prove the complete path.

## Phase C: Browser Streaming And Voice Audio

Goal:

- Turn assistance prototypes into high-value live operator modes after the real
  Hermes clearance loop works.

Scope:

- Add browser screenshot or stream transport.
- Add safe browser takeover protocol and return-control contract.
- Add mobile voice recording for supported targets.
- Add push-to-talk audio capture and playback.
- Evaluate WebRTC for browser and voice streaming.
- Keep all live media modes self-hosted and Tailscale-first.

Exit criteria:

- Operator can inspect browser state during a blocked web action.
- Operator can send voice input without external provider dependency.
- Streaming modes have clear permissions, audit metadata, and failure states.

## Top Three Implementation Priorities

1. Hardware-backed mobile signing and key lifecycle hardening.
2. Allowlisted, secret-safe notification composition.
3. Real Hermes runtime clearance and assistance bridge.
