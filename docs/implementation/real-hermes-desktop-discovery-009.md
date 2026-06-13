# Real Hermes Desktop Discovery and Validation 009

Sprint: `HERMES-MCP-REAL-HERMES-CLIENT-008` real-desktop addendum

This pass preferred the installed Hermes Desktop environment over the HMCP
runtime simulation. It discovered and launched the local desktop app, verified
its loopback backend, mapped real approval/notification/assistance integration
points, and documented the bridge still required before HMCP can claim a true
desktop-to-mobile runtime loop.

## Safety Posture

- Non-destructive discovery only.
- No unrelated user data was modified.
- `.env` was located but not opened or printed.
- Config inspection was limited to redacted shape and key names.
- Session database inspection was limited to table names and session metadata,
  not message bodies.
- Desktop activation used computer control only to launch/inspect Hermes.

## Hermes Installation Discovered

| Area | Finding |
| --- | --- |
| Desktop app | `/Applications/Hermes.app` |
| Bundle identifier | `com.nousresearch.hermes` |
| Version | `0.15.1` |
| Release date reported by backend | `2026.5.29` |
| Electron app bundle | `/Applications/Hermes.app/Contents/Resources/app.asar` |
| Runtime root | `/Users/mhedhli/.hermes/hermes-agent` |
| Runtime venv | `/Users/mhedhli/.hermes/hermes-agent/venv` |
| CLI shim | `/Users/mhedhli/.local/bin/hermes` |
| Hermes CLI | `/Users/mhedhli/.hermes/hermes-agent/venv/bin/hermes` |
| Agent CLI | `/Users/mhedhli/.hermes/hermes-agent/venv/bin/hermes-agent` |
| ACP CLI | `/Users/mhedhli/.hermes/hermes-agent/venv/bin/hermes-acp` |
| Config | `/Users/mhedhli/.hermes/config.yaml` |
| Secret env file | `/Users/mhedhli/.hermes/.env`, not read |
| State database | `/Users/mhedhli/.hermes/state.db` |
| Desktop support data | `/Users/mhedhli/Library/Application Support/Hermes` |
| macOS preferences | `/Users/mhedhli/Library/Preferences/com.nousresearch.hermes.plist` |

## Runtime and Desktop Backend

Launching Hermes Desktop starts:

```text
/Applications/Hermes.app/Contents/MacOS/Hermes
/Users/mhedhli/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main dashboard --no-open --tui --host 127.0.0.1 --port 9120
```

The desktop backend is loopback-only and listens in the `9120-9199` range.
During validation it was active at `127.0.0.1:9120`.

Verified public status endpoint:

```text
GET http://127.0.0.1:9120/api/status
```

Returned:

```json
{
  "version": "0.15.1",
  "release_date": "2026.5.29",
  "hermes_home": "/Users/mhedhli/.hermes",
  "config_path": "/Users/mhedhli/.hermes/config.yaml",
  "env_path": "/Users/mhedhli/.hermes/.env",
  "config_version": 26,
  "latest_config_version": 26,
  "gateway_running": false,
  "active_sessions": 0,
  "auth_required": false,
  "auth_providers": []
}
```

Verified protected endpoint behavior:

```text
GET http://127.0.0.1:9120/api/sessions
```

returned `401 Unauthorized` without the ephemeral desktop session token.

## Configuration and Logs

Discovered config sections relevant to HMCP:

- `approvals`: mode, timeout, cron mode, destructive slash confirmation, MCP
  reload confirmation.
- `gateway`: strict mode and media delivery trust controls.
- `display`: background process notifications, long-running notifications,
  interface, streaming, tool progress, runtime footer.
- `voice`, `tts`, `stt`: installed voice configuration shape.
- `hooks` and `hooks_auto_accept`: hook system entry points.
- `browser`: browser engine, private URL policy, CDP URL, session recording.
- `tools`: tool search configuration.
- `auxiliary.approval`: auxiliary approval model configuration.

Discovered logs:

- `/Users/mhedhli/.hermes/logs/desktop.log`
- `/Users/mhedhli/.hermes/logs/agent.log`
- `/Users/mhedhli/.hermes/logs/errors.log`
- `/Users/mhedhli/.hermes/logs/gui.log`
- `/Users/mhedhli/.hermes/logs/bootstrap-installer.log`

Desktop log confirmed runtime startup:

- backend resolution
- open local port selection
- Hermes runtime readiness
- backend launch from `/Users/mhedhli/.hermes/hermes-agent`
- dashboard readiness

## Task and Session Identifiers

The installed state database contains `sessions` and `messages` tables plus FTS
indexes. Recent session metadata was present with IDs:

- `20260608_185726_7ec3a2`
- `20260608_182949_093e54`

Only session metadata was inspected. Message content was not read.

## Extension and Plugin Locations

Discovered relevant locations:

- `/Users/mhedhli/.hermes/hermes-agent/plugins`
- `/Users/mhedhli/.hermes/hermes-agent/apps/desktop`
- `/Users/mhedhli/.hermes/hermes-agent/apps/shared`
- `/Users/mhedhli/.hermes/hermes-agent/ui-tui`
- `/Users/mhedhli/.hermes/hermes-agent/plugins/hermes-achievements`
- dashboard plugin routes under `/api/dashboard/plugins`
- dashboard agent plugin install/enable/disable/update endpoints

These are plausible extension points for a future `hermes-mobile-control-plane`
desktop/runtime bridge, but no HMCP bridge plugin is installed today.

## Policy Hooks and Approval Paths

Real approval integration points exist in the installed runtime:

- `/Users/mhedhli/.hermes/hermes-agent/tools/approval.py`
- `/Users/mhedhli/.hermes/hermes-agent/acp_adapter/permissions.py`
- `/Users/mhedhli/.hermes/hermes-agent/gateway/platforms/api_server.py`
- `/Users/mhedhli/.hermes/hermes-agent/gateway/run.py`

Important observed behavior:

- `tools.approval` is the dangerous-command approval source of truth.
- It has per-session pending approval queues.
- It exposes `register_gateway_notify(session_key, cb)`.
- It fires `pre_approval_request` and `post_approval_response` plugin hooks.
- It blocks the agent thread until user approval, denial, or timeout.
- Silence is treated as non-consent.
- ACP integration maps approval choices into Hermes semantics: once, session,
  always, deny.

This is the best candidate for the HMCP approval bridge. A safe bridge should
wrap the gateway notify callback or ACP permission callback and call the HMCP
runtime client instead of trying to bypass Hermes approval internals.

## Assistance Paths

Real assistance-like integration points exist:

- `/Users/mhedhli/.hermes/hermes-agent/tools/clarify_gateway.py`
- `/Users/mhedhli/.hermes/hermes-agent/apps/shared/src/json-rpc-gateway.ts`
- `/Users/mhedhli/.hermes/hermes-agent/ui-tui/src/gatewayTypes.ts`

Observed event names include:

- `clarify.request`
- `approval.request`
- `sudo.request`
- `secret.request`
- `background.complete`

`tools.clarify_gateway` stores pending clarify requests, registers per-session
notify callbacks, waits with timeout, and unwinds when a session ends. This is
the closest installed Hermes path to HMCP TUA assistance. A future bridge should
map `clarify.request` into HMCP TUA or a narrower "needs user input" session.

## Notification Paths

Real notification integration points exist:

- Desktop Electron preload exposes `hermesDesktop.notify`.
- Electron main handles `hermes:notify` and displays a native Notification.
- Runtime config has `display.background_process_notifications`.
- `tools/terminal_tool.py` supports `notify_on_complete`.
- `gateway/run.py` and platform adapters contain user notification paths for
  long-running tasks, restarts, gateway messages, and platform delivery events.

These are notification surfaces inside Hermes. They are not yet connected to
HMCP `mobile_notify`.

## APIs, Sockets, and IPC

Discovered desktop API and socket surfaces:

- Public REST: `/api/status`
- Protected REST: `/api/sessions`, `/api/config`, `/api/logs`, `/api/ops/*`,
  `/api/pairing`, `/api/gateway/start`, `/api/gateway/stop`,
  `/api/dashboard/plugins`, and related dashboard endpoints.
- JSON-RPC WebSocket: `/api/ws`
- PTY WebSocket: `/api/pty`
- Event broadcast sockets: `/api/pub` and `/api/events`
- Electron IPC: `hermes:api`, `hermes:notify`, `hermes:terminal:start`,
  `hermes:terminal:write`, `hermes:terminal:resize`,
  `hermes:terminal:dispose`.

The desktop main process creates the dashboard WebSocket URL using the
ephemeral session token. External scripts should not scrape this token from
private process state. A proper HMCP bridge should use a supported local runtime
hook instead.

## Desktop Validation Performed

Computer-control actions:

- Activated `/Applications/Hermes.app` using the computer control tool.
- No clicks, typing, destructive commands, or settings changes were performed.

Terminal validation:

- Located Hermes app and runtime files.
- Parsed the desktop bundle metadata.
- Confirmed the desktop process and spawned Python backend.
- Verified loopback listener on `127.0.0.1:9120`.
- Probed `/api/status`.
- Confirmed `/api/sessions` rejects unauthenticated access.
- Inspected logs for runtime readiness.
- Inspected the state database schema and session metadata.
- Inspected source-level approval, clarify, notification, API, socket, and IPC
  integration candidates.

## Real vs Simulated Paths Exercised

| Path | Real Hermes exercise | HMCP end-to-end status | Reason |
| --- | --- | --- | --- |
| Approval | Real approval hooks discovered in installed runtime. Desktop backend launched and protected API validated. | Not completed through desktop. Existing HMCP runtime E2E remains simulation-backed. | No installed bridge forwards `tools.approval` or ACP permission callbacks into HMCP Gateway. |
| Notification | Real desktop notification IPC and runtime notification surfaces discovered. | Not completed through desktop. HMCP `mobile_notify` remains gateway/runtime-client driven. | No Hermes tool or plugin currently calls HMCP `mobile_notify`. Electron notification IPC is renderer-local. |
| Assistance | Real clarify request/store/wait path discovered. JSON-RPC event type exists. | Not completed through desktop. HMCP TUA remains runtime-client driven. | No installed bridge maps `clarify.request` or assistance callbacks into HMCP TUA sessions. |
| Waiting state and resume | Desktop runtime has blocking approval and clarify waits with timeout semantics. | Not completed through desktop. | HMCP cannot yet resolve a real desktop wait because Hermes has no HMCP callback registered. |

## Fallback Justification

The prior `gateway/scripts/hermes_runtime_e2e.py` smoke remains a
Hermes-compatible simulation, not proof of installed desktop integration.
Fallback was necessary for full approval/TUA/browser/voice loops because the
installed desktop runtime exposes hooks but does not yet have an HMCP bridge
installed at those hooks.

What was attempted:

- Installed desktop discovery.
- Desktop launch.
- Loopback backend probing.
- Protected endpoint probing.
- Runtime source inspection.
- Approval hook discovery.
- Clarify assistance hook discovery.
- Notification path discovery.
- Session database and log metadata inspection.

What is required for real integration:

- A Hermes-side bridge module installed into the local runtime or plugin system.
- Approval bridge from `tools.approval.register_gateway_notify` or
  `acp_adapter.permissions.make_approval_callback` into `HermesRuntimeClient`.
- Clarify bridge from `tools.clarify_gateway` into HMCP TUA sessions.
- `mobile_notify` registered as a Hermes tool or runtime helper.
- Safe test trigger for a real approval request that does not execute a
  destructive shell command.
- Supported desktop/runtime authentication path for bridge code, without token
  scraping.
- Mapping from Hermes session IDs to HMCP mission IDs.

## Probe Script

Added:

```text
gateway/scripts/real_hermes_desktop_probe.py
```

Usage:

```bash
uv run --project gateway python gateway/scripts/real_hermes_desktop_probe.py
```

The probe reports:

- installation paths and version
- runtime paths
- redacted config shape
- loopback desktop backend status
- protected endpoint status
- log file metadata
- process commands
- state database table/session metadata
- integration candidate paths

It does not read `.env`, does not read message contents, and does not modify the
Hermes install.

## Recommended Next Implementation

1. Add an opt-in Hermes runtime bridge module outside Hermes core first, using
   `HermesRuntimeClient` and loopback-only HMCP Gateway calls.
2. Bridge dangerous approval requests by wrapping the existing Hermes approval
   notify callback and returning HMCP signed mobile decisions to Hermes.
3. Bridge clarify requests into HMCP TUA sessions and return user summaries or
   direct text responses.
4. Add `mobile_notify` as a Hermes tool/helper so notifications originate from
   real Hermes execution.
5. Add a non-destructive installed-Hermes smoke harness that imports the real
   installed approval/clarify modules and proves the bridge contract before
   wiring it into live desktop sessions.
6. Only after the harness passes, add a desktop plugin or supported hook
   installation flow.
