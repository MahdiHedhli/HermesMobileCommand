# TUI PTY Prototype 004

Sprint: `HERMES-MCP-TUI-PTY-PROTOTYPE-004`

## Summary

This slice adds the first functional terminal path for Hermes Mobile Control
Plane:

1. The mobile app creates a signed TUI session through the gateway.
2. The gateway starts a development-only local PTY when explicitly enabled.
3. The mobile app opens a WebSocket stream for terminal I/O.
4. The user can send input, paste text, use common accessory keys, detach, close,
   and copy scrollback.

The PTY runner is a prototype. It is secure-by-default because it is disabled
unless explicitly enabled, but it is not production-hardened shell execution.

## Gateway Endpoints

Signed paired-device REST endpoints:

- `POST /v1/tui/sessions`
- `GET /v1/tui/sessions`
- `GET /v1/tui/sessions/{session_id}`
- `POST /v1/tui/sessions/{session_id}/detach`
- `POST /v1/tui/sessions/{session_id}/close`

Terminal stream endpoint:

- `GET /v1/tui/sessions/{session_id}/stream?access_token=<paired-access-token>`

The WebSocket stream is only useful after a session has already been created by
a signed request. The alpha stream uses the paired device access token; future
hardening should mint a short-lived attach token from a signed request.

## WebSocket Protocol

Client to gateway:

- `{"type":"input","data":"ls\n"}`
- `{"type":"paste","data":"multi\nline\n"}`
- `{"type":"resize","rows":24,"cols":80}`
- `{"type":"ping"}`
- `{"type":"detach"}`
- `{"type":"close"}`

Gateway to client:

- `{"type":"output","session_id":"...","data":"..."}`
- `{"type":"state","session_id":"...","state":"active"}`
- `{"type":"error","message":"..."}`
- `{"type":"pong","session_id":"..."}`
- `{"type":"audit_notice","message":"..."}`

## Safety Controls

Local PTY execution is disabled unless:

```bash
export HERMES_TUI_ENABLE_LOCAL_PTY=1
```

Additional controls:

- `HERMES_TUI_ALLOWED_COMMANDS`: comma-separated exact command paths. Defaults
  to `/bin/sh`.
- `HERMES_TUI_DEFAULT_COMMAND`: command used when the mobile client does not
  request one. Defaults to `/bin/sh`.
- `HERMES_TUI_ALLOWED_WORKING_DIRECTORY`: root that all requested working
  directories must stay inside. Defaults to `.`.
- `HERMES_TUI_MAX_SESSIONS`: maximum open TUI sessions. Defaults to `2`.
- `HERMES_TUI_IDLE_TIMEOUT_SECONDS`: idle cleanup threshold. Defaults to `900`.

Gateway behavior:

- Missing or invalid device signatures reject REST controls.
- Revoked devices cannot create or control TUI sessions.
- Unknown sessions and sessions owned by another device are rejected.
- Non-allowlisted commands are rejected.
- Working directories outside the allowed root are rejected.
- Full terminal contents are not written to audit by default.
- Session creation, detach, close, input metadata, and paste metadata are
  audited.

## Mobile Behavior

The TUI screen now uses gateway-backed terminal mode when the runtime is paired
and the gateway accepts the TUI session. If the gateway is unpaired, disabled, or
rejects PTY policy, the screen falls back to mock terminal mode.

Functional mobile controls:

- Send typed input.
- Paste clipboard text as a paste frame.
- Copy scrollback.
- Detach session.
- Close session.
- Accessory keys: `ESC`, `TAB`, `CTRL+C`, arrows, `/`, `|`, `~`, brackets,
  function keys, Home, End, PgUp, PgDn.

`ALT` and `CMD` are intentionally treated as planned/no-op keys in the alpha.

## Local Demo

Start a dev gateway with local PTY enabled:

```bash
HERMES_TUI_ENABLE_LOCAL_PTY=1 \
HERMES_TUI_ALLOWED_COMMANDS=/bin/cat,/bin/sh \
HERMES_TUI_DEFAULT_COMMAND=/bin/cat \
HERMES_TUI_ALLOWED_WORKING_DIRECTORY="$(pwd)" \
uv run --project gateway uvicorn hermes_gateway.app:create_app \
  --factory --host 127.0.0.1 --port 8787
```

Then:

1. Run the Flutter app.
2. Set gateway URL to `http://127.0.0.1:8787/v1`.
3. Pair the app in Settings.
4. Open a TUI session from Approval More or the TUI route.
5. Type or paste text and verify terminal output.
6. Use Detach or Close from the terminal header.

For `/bin/cat`, typed input should echo back. For `/bin/sh`, use normal shell
commands only in a disposable development directory.

## Hardening Gaps Before Production

- Replace access-token WebSocket auth with short-lived signed attach tokens.
- Introduce a terminal broker or tmux-scoped workflow instead of raw local shell.
- Add policy checks tied to approval context, node risk, and device capability.
- Add shell command sandboxing or OS-level containment.
- Add output retention controls and redaction for any future backfill.
- Add structured paste warnings for control characters and secret-looking text.
- Add per-device and per-node TUI capability grants.
- Add stronger orphan cleanup and process supervision for long-running sessions.
