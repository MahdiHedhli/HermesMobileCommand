# ACT-009 — Hermes clearance plugin (real Hermes → ACT → phone)

**Plugin**: [integrations/hermes/act-clearance/](../../integrations/hermes/act-clearance/)
**Branch**: `003-mobile-beta` · **Date**: 2026-06-19

Wires the **real Hermes agent** (`~/.hermes/hermes-agent`, a separate product) to the
ACT gateway so risky agent tool calls require operator approval on the paired
Secure-Enclave phone. This is the Hermes-side integration anticipated as "a plugin for
Hermes" — ACT itself was already complete; nothing in Hermes called it before.

## Design

Hermes exposes a `pre_tool_call` block hook (`hermes_cli/plugins.py`,
`agent/agent_runtime_helpers.py` → `get_pre_tool_call_block_message`). A hook returns
`None` to allow a tool, or `{"action": "block", "message": ...}` to refuse it.

The `act-clearance` plugin registers that hook. For tools in the gated set it:

1. Raises a clearance on ACT — `POST /v1/hermes/tools/approval_requested`
   (only the tool name + argument **keys** are sent; raw values are never forwarded).
2. **Blocks** the tool, polling `POST /v1/hermes/tools/approval_status`, until the
   operator decides on the phone.
3. `approved` → return `None` (tool runs). `denied`/`expired`/`cancelled`/timeout/
   gateway-error → **block** (FAIL CLOSED).

Pure standard library (no deps), so it runs in any Hermes venv.

## Safety / sandboxing (two independent gates)

- **Hermes opt-in**: a user plugin in `~/.hermes/plugins/<name>/` only loads if its name
  is in `plugins.enabled` (config.yaml). Installing the files is inert otherwise.
- **Env gate**: even when loaded, every hook returns `None` unless
  `ACT_CLEARANCE_ENABLED=1`. So it cannot disrupt a live agent that hasn't opted in.

## Configuration (env)

| Var | Default | Meaning |
|---|---|---|
| `ACT_CLEARANCE_ENABLED` | off | `1` to activate (hard gate) |
| `ACT_GATEWAY_URL` | `http://127.0.0.1:8788/v1` | ACT gateway base URL |
| `ACT_CLEARANCE_GATED_TOOLS` | conservative high-impact set | CSV of gated tools; `*` = all |
| `ACT_CLEARANCE_RISK_FAMILY` | `external_effect` | risk_family to request |
| `ACT_CLEARANCE_TIMEOUT` | `180` | seconds to wait for a decision |
| `ACT_CLEARANCE_POLL` | `2` | poll interval seconds |

## Verification (sandbox, 2026-06-19)

Tested by invoking the `pre_tool_call` hook directly (so it can't touch the live agent),
pointed at the live ACT gateway, with the **real paired iPhone** approving.

| Case | Result |
|---|---|
| Disabled (no `ACT_CLEARANCE_ENABLED`) | `None` (no-op) ✓ |
| Non-gated tool (`read_file`) | `None` (allow) ✓ |
| Gateway unreachable | **block** (fail-closed) ✓ |
| Timeout, no approval (180s/4s) | **block** (fail-closed) ✓ |
| **Approve on phone** (`git_push`) | `None` after 70s → **tool released**; gateway shows `approved`/`once` by the `p256` Secure-Enclave device ✓ |

So the full chain is real: **Hermes `pre_tool_call` hook → ACT `/hermes/tools/approval_requested`
→ phone (real Secure Enclave P-256 + Face ID) → decision → tool released/blocked.**

## Enabling in a real Hermes session

1. Install: copy `integrations/hermes/act-clearance/` → `~/.hermes/plugins/act-clearance/`.
2. Enable in Hermes: `hermes plugins enable act-clearance` (adds to `plugins.enabled`).
3. Run the session with: `ACT_CLEARANCE_ENABLED=1 ACT_GATEWAY_URL=http://127.0.0.1:8788/v1 hermes …`.

## Honest limits / open bugs

- **Verified via direct hook invocation**, not yet inside a full Hermes agent run where a
  model drives a real gated tool call. The hook contract + fail-closed/allow behavior are
  proven; the in-agent wiring (config-enable + a real tool call) is the remaining step.
- **BUG — ACT should push-notify the phone for clearances.** Today the only realtime
  channel is the WebSocket event stream, and `push_dispatch` is `unavailable` (no APNs).
  When the app is backgrounded or the stream drops, the operator is **not alerted** — they
  must open/refresh the app. Real APNs (or another push) is needed for production usability.
- **GAP — WS stream access-token is not auto-refreshed.** The paired-device access token
  has a 15-min TTL; after it expires the WS `/v1/events/stream` returns `403` and live
  delivery silently stops (the signed REST path still works on manual refresh). The app
  should refresh the token (or re-establish the stream) before expiry.
- Risk mapping is a static tool list; it does not yet consult ACT's capability registry to
  derive `risk_family` per tool.
