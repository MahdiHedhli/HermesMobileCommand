# Feature Specification: Hermes Control-Plane Bridge

**Feature Branch**: `003-mobile-beta` (continued)
**Created**: 2026-06-19
**Status**: Approved — building first slice
**Input**: Make the mobile app a first-class control surface for the REAL Hermes agent on ColPanicM2 — live dashboard/agents/fleet, task visibility (sessions, current plan/tool, activity), interactive questions + permission requests answered from the phone, interventions (pause/steer/stop), TUI, and notifications. Wire the real Hermes agent into the ACT gateway the app already reads.

## Summary

The app (Hermes Mobile Control Plane, spec 001) already has every surface and the ACT gateway already has every endpoint — today they render the gateway's **mock seed** data. This feature adds the **Hermes→ACT bridge**: an in-process Hermes **plugin** (extending `act-clearance` → `act-control`) that feeds the real agent's identity, session, and activity into the gateway and relays operator control back. ACT remains the control tower; Hermes is adapter #1. The proven trust model is unchanged: device-signed P-256 on all phone reads/decisions, hermes-local (loopback) on all plugin pushes, the fail-closed clearance gate, redaction discipline (tool name + arg keys only).

**Key finding:** `POST /v1/runtime/context` (hermes-local) is already the agent/session/mission **upsert** that drives the rows the app reads (`/v1/agents`, `/v1/inventory`, `/v1/sessions`, `/v1/missions`). So the monitoring plane needs **no new gateway endpoint** — only mapping Hermes hooks to that endpoint. Interactive questions reuse the existing `/v1/runtime/tua/requests` + `/result` pair. Only later phases (interventions, fleet liveness, TUI) need additive gateway work.

## Architecture (decided)

In-process **plugin**, not a sidecar: only an in-process hook can (a) receive correlated hook kwargs synchronously, (b) **block** a tool via `pre_tool_call` (the proven clearance gate), and (c) reach the live agent object for control-back. A `:9120` poller is rejected for the primary path.

Two planes meet in the gateway store:
- **Monitoring (Hermes→ACT, push):** plugin hooks → hermes-local `POST /v1/runtime/context` (+ `/v1/nodes/register` once, notifications) → gateway upserts agent/session/mission + emits events → phone reads via device-signed GETs + the WS event tickle.
- **Control (ACT→Hermes, pull):** phone issues a device-signed command → gateway records it → plugin polls a hermes-local drain → applies to the live agent. Interactive questions use the TUA request/result loop (no agent-object access needed).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See and follow the real agent (Priority: P1)

The operator opens the app and sees the **real ColPanicM2 agent** (not a mock) — its status, current session, and current tool update live as the agent works.

**Independent Test**: Run ColPanicM2; confirm Home/Agents/agent-detail show the real agent with live status/tool, and the mock agent is gone.

**Acceptance Scenarios**:
1. **Given** ColPanicM2 starts a session, **When** the operator opens Agents, **Then** the real agent appears `running` with its session.
2. **Given** the agent calls a tool, **When** the operator views it, **Then** `current_tool`/`current_target` update live.
3. **Given** the agent finishes, **When** the operator views it, **Then** status returns to `idle`.

### User Story 2 - Answer the agent's question from the phone (Priority: P1)

When the agent needs operator input, the question appears on the phone; the operator answers, and the agent continues with that answer.

**Independent Test**: The agent calls a designated "ask" tool; the question appears in the app's TUA surface; the operator replies; the agent receives the reply and proceeds.

**Acceptance Scenarios**:
1. **Given** the agent asks a question, **When** it reaches the gateway, **Then** an assistance request appears on the phone (composed/redacted, never raw).
2. **Given** the operator answers and returns control, **When** the plugin polls, **Then** the agent receives the operator's answer and continues.
3. **Given** no answer within the window, **Then** the call fails closed (the agent is told it was not answered).

### User Story 3 - Intervene, TUI, notifications (Priority: P2)

Pause/steer/stop a running agent; drive its terminal; receive push alerts. (Later phases.)

### Edge Cases
- Plugin/Hermes dies without a final status → fleet must not show "online" forever (liveness reaper, phase 3).
- `on_session_end` fires per-turn, not at true teardown → must not flap status.
- High tool frequency → `/v1/runtime/context` posts must be debounced.
- node_id mismatch → sessions/agents 404; always default to the gateway's node_id.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The bridge MUST be an in-process Hermes plugin (extend `act-clearance`), default-OFF (`ACT_CLEARANCE_ENABLED`) and opt-in via Hermes `plugins.enabled`.
- **FR-002**: On session/tool lifecycle hooks, the plugin MUST upsert the real agent/session/mission via hermes-local `POST /v1/runtime/context` (debounced), mapping a stable `agent_id` (env) and the gateway's `node_id`.
- **FR-003**: The gateway MUST allow disabling the mock data seed (env flag) so the fleet shows only real agents; default preserves existing behavior/tests.
- **FR-004**: For designated "question" tools, the plugin MUST raise a TUA assistance request and block until the operator answers (or a timeout), returning the operator's answer to the agent; fail-closed on timeout/error.
- **FR-005**: All phone-facing reads/decisions remain device-signed P-256; all plugin pushes remain hermes-local (loopback); redaction (tool name + arg keys only) is preserved.
- **FR-006** (phase 2): Interventions — the gateway durably queues operator commands; the plugin drains them and applies pause/steer/stop to the live agent; the app gains an intervention call.
- **FR-007** (phase 3): Fleet liveness — node/agent health derives from last-seen with a stale→offline reaper.
- **FR-008** (phase 5): TUI — a read-only mirror of the agent's terminal output to the phone, then bidirectional.

### Key Entities
- **Bridge plugin** (`act-control`), **Runtime context** (agent/session/mission upsert), **Assistance request** (interactive question), **Intervention command** (phase 2).

## Success Criteria *(mandatory)*
- **SC-001**: The real ColPanicM2 agent appears in the app with live status/session/tool; no mock agent.
- **SC-002**: An agent question is answered from the phone and the agent continues with that answer — end-to-end, live.
- **SC-003**: Gateway pytest stays green (mock-seed gating default-preserves); ACT-001..007 unchanged.

## Build Plan (phased)
1. **First slice (this build):** mock-seed env-gate (gateway) + monitoring hooks (`on_session_start`/`pre_tool_call`/`post_tool_call`/`on_session_end` → `/v1/runtime/context`) + interactive-question TUA relay (plugin). Zero app changes.
2. Interventions (gateway command queue + plugin drain + app call).
3. Fleet liveness reaper; `current_plan` passthrough.
4. Streamed per-tool activity timeline.
5. TUI terminal mirror (read-only → bidirectional).

## Non-Goals (this slice)
- TUI terminal, interventions, push-delivery (APNs pending `.p8`), multi-agent/subagent fan-out, the `:9120` sidecar feed.

## Assumptions
- Single real agent (`ACT_CLEARANCE_AGENT_ID=colpanic_m2`) under the gateway's default `node_id`.
- The plugin reaches the gateway on loopback at the operator-set `ACT_GATEWAY_URL`.
