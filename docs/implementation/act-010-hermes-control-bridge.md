# ACT-010 — Hermes control-plane bridge (real agent → phone, live)

**Plugin**: [integrations/hermes/act-clearance/](../../integrations/hermes/act-clearance/)
**Spec**: [specs/004-hermes-control-bridge/spec.md](../../specs/004-hermes-control-bridge/spec.md)
**Branch**: `003-mobile-beta` · **Date**: 2026-06-19

Extends the ACT-009 clearance plugin into a two-way **control-plane bridge** so the
operator's phone is a first-class surface for the **real Hermes agent** on ColPanicM2 —
not just an approval gate. The app already had every screen and the ACT gateway already
had every endpoint; they rendered the gateway's **mock seed**. This wires the real agent
in.

## What it adds (on top of the clearance gate)

| Plane | Mechanism | Result on the phone |
|---|---|---|
| **Monitoring** (Hermes → ACT) | `on_session_start` / `pre_tool_call` / `post_tool_call` / `on_session_end` hooks → hermes-local `POST /v1/runtime/context` | Home / Agents / agent-detail / Missions show the **real** agent live (status, session, current tool) |
| **Interactive questions** (Hermes → phone → Hermes) | a designated "ask" tool (`clarify`) routed via `pre_tool_call` → `POST /v1/runtime/tua/requests`, block-poll `GET …/{id}/result` → answer returned to the agent | the agent's question appears in the app's **Assistance/TUA** surface; the operator's answer flows back and the agent continues |
| **Clearance** (unchanged, ACT-009) | `pre_tool_call` → `/v1/hermes/tools/approval_requested` + poll | risky tools block until approved on the phone (fail-closed) |

**Key architectural finding:** `POST /v1/runtime/context` (hermes-local) is already the
agent/session/mission **upsert** that drives the rows the app reads (`/v1/agents`,
`/v1/inventory`, `/v1/sessions`, `/v1/missions`). So monitoring needs **no new gateway
endpoint** — only mapping Hermes hooks to it. Interactive questions reuse the existing
`/v1/runtime/tua/requests` + `/result` pair. The bridge declares the `tua`/`tui`/
`browser_assist`/`voice` capabilities on the agent (via the context push) so the gateway
permits operator-guidance handoffs (`require_runtime_capability`).

## Trust model (unchanged from ACT-001..009)

- Phone reads/decisions: device-signed P-256 (Secure Enclave), redaction (tool name +
  arg **keys** only).
- Plugin pushes: hermes-local (loopback only).
- Monitoring hooks fail **OPEN** (a gateway hiccup never blocks the agent); the clearance
  gate and the question relay fail **CLOSED**.
- Two independent enable gates: Hermes `plugins.enabled` **and** `ACT_CLEARANCE_ENABLED=1`.

## Configuration (env, additions)

| Var | Default | Meaning |
|---|---|---|
| `ACT_CLEARANCE_AGENT_ID` | `hermes_agent` | stable agent id the phone sees (e.g. `colpanic_m2`) |
| `ACT_CLEARANCE_AGENT_NAME` | `Hermes Agent` | display name |
| `ACT_QUESTION_TOOLS` | `clarify,ask_operator,ask_user` | CSV of tools routed to the phone as questions; `*` = all |

(Plus the ACT-009 vars: `ACT_GATEWAY_URL`, `ACT_CLEARANCE_GATED_TOOLS`,
`ACT_CLEARANCE_TIMEOUT`, `ACT_CLEARANCE_POLL`, `ACT_CLEARANCE_RISK_FAMILY`.)

## Gateway change

One additive, default-preserving change: `ACT_SEED_MOCK_DATA` (default on) gates
`store.seed_mock_data` so a real deployment shows only real, bridge-fed agents
(`gateway/src/hermes_gateway/config.py`, `app.py`). Gateway pytest stays green (151).

## App-side fix (required for the question round-trip)

The first live test surfaced an app gap: the inbox never sourced **real** TUA requests
(`GatewayAlphaRepository.loadHome/loadInbox` built assistance items only from
notifications, with `id = notificationId`; `/tua/requests` was never fetched). So a real
agent question had no tappable inbox entry carrying its `requestId`, and tapping assistance
fell back to a hardcoded mock session (`'assist-release'`). Fixed in `mobile/`:

- `GatewayAlphaRepository` gains a `TuaRepository` dependency; `loadHome`/`loadInbox` fetch
  `GET /tua/requests`, filter to operator-actionable states (requested/active/
  waiting_on_user/user_controlling — there is no `open` state), and emit assistance
  `InboxItem`s with `id = requestId`, de-duplicating the notification-derived assistance.
- `tua_screen.dart`: removed the `'assist-release'` mock default and the paired-mode
  fall-through to `MockAlphaRepository` (a real `requestId` now drives `createSession`; an
  unknown/empty id shows an explicit empty state, never mock data).
- `inbox_screen.dart`: security branch no longer pushes the hardcoded `'appr-network'`.
- Unit test (`operator_repositories_test.dart`): a real TUA request becomes exactly one
  assistance item with `id == requestId`; closed requests and the `agent_blocked`
  notification do not duplicate it.

## Verification (2026-06-19) — honest levels

Live gateway on `0.0.0.0:8788` (seed off, mock rows cleared), real paired iPhone
(`dev_MeQu39Y18hSd`, p256 / mobile_signed / `intervene` permission), real Hermes one-shot
(`hermes --yolo -z …`) with the plugin enabled.

Two gateway-contract conformances were needed for the question round-trip (no
gateway code changed — the plugin was made to conform):

1. **Capability** — declare `tua`/`tui`/`browser_assist`/`voice` in the context push,
   else `POST /v1/runtime/tua/requests` 403s `runtime lacks tua capability`.
2. **Risk family** — raise questions with a **low-risk** family (`read_only`), not
   `external_effect`. `engage_handoff` requires a *bound approved clearance* for non-low-risk
   handoffs (`LOW_RISK_FAMILIES = {observe, read_only, routine}`), so an `external_effect`
   question 403s `missing_clearance` when the operator taps to engage. A question is not a
   risky action, so `read_only` is correct.
3. **Answer extraction** — the operator's answer is their typed **message**, not the app's
   generic `return_summary` ("Operator returned control from mobile") nor the createSession
   boilerplate ("Opened from Agentic Control Tower."); the poll returns the latest non-
   boilerplate user reply.

| Case | Level | Result |
|---|---|---|
| **Monitoring — real agent upserted** | gateway-verified | one-shot ran a tool; gateway `agents` shows `colpanic_m2` / `ColPanicM2` with a real Hermes session; no mock agent ✓ |
| **Monitoring — app reads the real agent** | device-verified | updated build on the iPhone fetched `GET /v1/inventory`,`/agents`,`/tua/requests` → `200` ✓ |
| **Question relay — request raised** | live-verified | agent called `clarify`; plugin `POST /v1/runtime/tua/requests` → `201`; agent **blocked** ✓ |
| **TUA inbox surfaces the real question** | device-verified | the question appeared as an `Agent needs your input` inbox item carrying the real `requestId`; tapping it → `POST /v1/tua/requests/{id}/sessions` → `201` real session by `dev_MeQu39Y18hSd` (no mock, no 403) ✓ |
| **Question round-trip (agent → phone → agent)** | device-verified | agent asked "staging or production?"; operator typed **"staging"** on the Secure-Enclave device (`messages` 201, `return-control` 200 → `returned_to_agent`); plugin poll returned "staging"; **agent reported "staging" verbatim** ✓ |
| Capability gate (`tua`) | live-verified | fixed by declaring capabilities in the context push ✓ |
| Risk-family / clearance gate | live-verified | `external_effect` question 403'd `missing_clearance` on engage; `read_only` engages cleanly ✓ |
| TUA inbox fix | unit + device-verified | `flutter analyze` clean, `flutter test` 42 passed; exercised live on-device ✓ |
| Gateway pytest (seed-gate + push) | green | 151 passed ✓ |

## Honest limits

- This is the **first slice**. Interventions (pause/steer/stop), fleet liveness reaper,
  per-tool activity timeline, and the TUI mirror are designed (spec §Build Plan phases
  2–5) but **not yet built**.
- Question round-trip uses the TUA poll loop (no live-agent-object access), which sidesteps
  the gateway-mode `inject_message` limitation; true interventions (phase 2) will reach the
  live `AIAgent` object directly.
- `on_session_end` fires per-turn; the bridge only reflects a terminal status when the turn
  actually completed/was interrupted (avoids status flapping).
- Push delivery (APNs) still pending the operator's `.p8`; until then the phone is alerted
  via the live WS stream (manual refresh after it drops).
