# TUI Command Surface Finding

Date: 2026-06-18

Status: ACT-006 mitigation implemented.

## Summary

The ACT TUI local PTY surface is governed by operator PTY enablement,
the configured command allowlist, paired-device signatures, TUI capability
grants, tower-owned command risk classification, and bound clearance tiering
for high-risk command starts.

This is contained by default because local PTY execution is disabled unless the
operator sets `HERMES_TUI_ENABLE_LOCAL_PTY=1`. When enabled, however, the
command allowlist becomes a major trust boundary. The default allowlist contains
`/bin/sh`, but ACT now refuses shell entries while local PTY is enabled unless
the operator also sets the explicit shell opt-in flag. Allowing a shell remains
equivalent to allowing arbitrary command execution after attach, within the
process permissions of the gateway host. The configured working directory
constrains the requested starting directory; it is not a chroot or
operating-system sandbox.

The `risk_level` field on a TUI session remains a display label. Authorization
uses ACT's tower-owned command-to-`risk_family` map. Unmapped commands and shell
commands resolve to `external_effect`, which requires a bound mobile-tiered
clearance before the PTY starts.

## Threat Actor

The relevant actor is the untrusted agent sharing the gateway host: a backend or
agent process that can reach loopback services, observe local files, or interact
with gateway-local control surfaces. This actor is already tracked in the threat
model. TUI matters for this actor because a shell allowlist entry turns the TUI
surface into a local command execution path if the actor can obtain or reuse a
paired device credential or otherwise drive a signed TUI request.

## Evidence

### Default posture

- `Settings.tui_enable_local_pty` defaults to `False` while
  `tui_allowed_commands` and `tui_default_command` default to `/bin/sh`
  (`gateway/src/hermes_gateway/config.py:36-39`).
- `validate_tui_request` rejects session creation before command validation when
  local PTY is disabled (`gateway/src/hermes_gateway/tui.py:184-191`).
- The regression test confirms the default refusal response:
  `403 {"detail": "local TUI PTY is disabled"}`
  (`gateway/tests/test_tui.py:35-48`).

Finding: with defaults, `POST /v1/tui/sessions` cannot start a PTY.

### Allowlist semantics

- When PTY is enabled, `validate_tui_request` selects the request command or
  `settings.tui_default_command`, then requires exact membership in
  `settings.tui_allowed_commands`
  (`gateway/src/hermes_gateway/tui.py:193-198`).
- `LocalPtyManager.create_runtime` passes the selected command directly to
  `asyncio.create_subprocess_exec` and wires PTY input/output to that process
  (`gateway/src/hermes_gateway/tui.py:35-55`).
- TUI WebSocket input and paste frames call `tui_manager.write`, which writes
  caller-provided text to the PTY master file descriptor
  (`gateway/src/hermes_gateway/app.py:2449-2494`;
  `gateway/src/hermes_gateway/tui.py:94-99`).
- A read-only TestClient probe with `tui_enable_local_pty=True` and default
  command settings created an active session whose command was `/bin/sh`, then
  executed shell input that printed `$PWD`, created a file, and changed
  directory to `/`.
- The same probe confirmed creation with `working_directory="/"` was rejected
  with `403 {"detail": "TUI working directory is outside the allowed root"}`.
  This matches the validation path that resolves the requested directory and
  requires it to be under `tui_allowed_working_directory`
  (`gateway/src/hermes_gateway/tui.py:200-208`).

Finding: `/bin/sh` in the allowlist is equivalent to no meaningful command
allowlist for command execution after attach. ACT-006 makes that opt-in explicit
with `HERMES_TUI_ALLOW_SHELL_COMMANDS=1`; the configured workdir blocks a
requested start-directory escape, but it does not confine the shell after it
starts.

### Reachability and authorization

- `POST /v1/tui/sessions` uses the signed device dependency, requires device
  capability `tui`, validates command/workdir, and then requires node or agent
  TUI capability before creating and starting the runtime
  (`gateway/src/hermes_gateway/app.py:839-890`).
- `require_device_capability` accepts either a device permission matching
  `tui` or an active device capability grant
  (`gateway/src/hermes_gateway/capabilities.py:11-18`,
  `gateway/src/hermes_gateway/capabilities.py:28-65`).
- `_require_tui_capability` accepts either node capability `tui` or agent
  capability `tui` (`gateway/src/hermes_gateway/app.py:2297-2305`).
- The TUI tests grant `tui` to `agent_mock` and successfully create sessions,
  confirming an agent record is sufficient
  (`gateway/tests/test_tui.py:77-89`, `gateway/tests/test_tui.py:372-380`).
- Pairing start/complete are local ceremony endpoints that are not signed-device
  endpoints. `start_pairing` returns a pairing token, and `complete_pairing`
  creates a device using the pairing's requested permissions
  (`gateway/src/hermes_gateway/routers/identity.py:35-71`,
  `gateway/src/hermes_gateway/routers/identity.py:81-150`).

Finding: TUI is not operator-only in the node/agent capability sense; an agent
record with capability `tui` satisfies the backend capability check. The REST
creation path still requires a paired signed device with `tui` permission or a
device grant. A co-resident or loopback caller cannot use TUI only by advertising
agent capability, but could use it if it can obtain or reuse a paired device key
with `tui`, or if deployment exposure makes the local pairing ceremony available
to that caller.

### Channel policy and clearance binding

- Approval transitions call `enforce_clearance_channel` when approving
  (`gateway/src/hermes_gateway/app.py:2154-2184`).
- Tiered handoffs call `engage_handoff`, which requires a bound clearance for
  non-low-risk families (`gateway/src/hermes_gateway/handoff.py:14-85`).
- TUA, browser assistance, and voice routes call `_engage_handoff` at their
  handoff points (`gateway/src/hermes_gateway/app.py:1131-1154`,
  `gateway/src/hermes_gateway/app.py:1451-1460`,
  `gateway/src/hermes_gateway/app.py:1730-1739`).
- ACT-006 routes TUI start through `_require_tui_start_clearance` before
  `LocalPtyManager.create_runtime`.
- Low-risk command families (`observe`, `read_only`, `routine`) remain
  capability-gated.
- High-risk command families require a bound clearance that has already been
  approved through the discrete clearance path and therefore already passed
  channel eligibility.
- The TUI path reuses the ACT-005 bound-clearance checks instead of
  reimplementing channel policy: approved, not expired, not consumed, same node,
  same agent, same work reference, same command/workdir fingerprint, same risk
  family, and eligible recorded channel.
- The clearance is marked consumed on successful PTY start.

Finding: high-risk TUI command start is no longer untiered. `risk_level` remains
display-only; the tower-owned command risk map determines authorization.

## Route Inventory

| Route | Method | Auth/control dependency |
| --- | --- | --- |
| `/v1/tui/sessions` | `POST` | Signed paired-device request; device `tui` permission or grant; PTY enabled; command allowlist; allowed start directory; node or agent `tui` capability |
| `/v1/tui/sessions` | `GET` | Signed paired-device request; returns sessions owned by the signing device |
| `/v1/tui/sessions/{session_id}` | `GET` | Signed paired-device request; session must belong to the signing device |
| `/v1/tui/sessions/{session_id}/detach` | `POST` | Signed paired-device request; session must belong to the signing device |
| `/v1/tui/sessions/{session_id}/close` | `POST` | Signed paired-device request; session must belong to the signing device |
| `/v1/tui/sessions/{session_id}/attach-token` | `POST` | Signed paired-device request; device `tui` permission or grant; session must belong to the signing device |
| `/v1/tui/sessions/{session_id}/stream` | WebSocket | Short-lived attach token scoped to session and device; session must be running |

No separate `/runtime/tui` route or runtime-specific TUI command route was found
in the running code.

## Severity Recommendation

Recommendation: keep local PTY development-only until process isolation and
native device attestation improve, but ACT-006 closes the high-risk untiered
start gap.

Reasoning:

- Default risk is contained because local PTY is disabled by default.
- Enabled risk is materially higher when `/bin/sh` remains allowlisted because
  the allowlist no longer limits command execution.
- The existing route still requires a signed paired device and TUI capability,
  so this is not an unauthenticated remote shell by itself.
- High-risk command starts now follow the ACT-005 bound-clearance pattern.
- A co-resident untrusted agent is exactly the actor that benefits from any
  pairing exposure, device-key reuse, or overbroad TUI capability grant.

Residual risk remains if operators grant broad TUI capability, pair weak devices,
or opt into shell commands on hosts shared with untrusted agents.

## Non-default-changing Hardening Note

ACT refuses shell commands while local PTY is enabled unless
`HERMES_TUI_ALLOW_SHELL_COMMANDS=1` is set. This preserves the current disabled
default while making the allowlist trust boundary visible to operators who
explicitly enable TUI.
