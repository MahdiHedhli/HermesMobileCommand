# Mobile Native Realtime 003

Sprint: `HERMES-MCP-MOBILE-NATIVE-REALTIME-003`

## Scope

This slice makes the Flutter alpha feel closer to a mobile operator app while
staying within the approved control-plane architecture:

- Native readiness was inspected and documented.
- The mobile runtime now connects to the gateway WebSocket event stream.
- Home and Inbox refresh when gateway events arrive.
- Approval detail refreshes on approval lifecycle events.
- The Approval More menu now separates functional signed actions from planned
  intervention actions.
- The local demo gateway seeds multiple approvals and a notification for app
  testing.

## Event Stream Behavior

The mobile app connects to:

```text
ws://<gateway-host>/v1/events/stream?access_token=<paired-device-access-token>
```

Current authentication model:

- HTTP control requests use canonical Ed25519 signed device headers.
- The WebSocket stream uses the paired device access token in the query string.
- This matches the current gateway contract and is documented as an alpha model.
- Future native builds should move toward a stronger WebSocket handshake or
  short-lived stream token minted through a signed request.

Runtime behavior:

- The client parses gateway event envelopes into `GatewayEvent`.
- The last cursor is retained and used on reconnect.
- Reconnect uses exponential backoff.
- Home and Inbox listen to runtime event revisions and reload repository data.
- Manual refresh remains available as a fallback.

Events that drive UI freshness:

- `approval.requested`
- `approval.resolved`
- `notification.created`
- `agent.status`
- `agent.activity`
- `system.health`

## Advanced Approval Actions

Functional signed actions:

- Approve Once: `POST /v1/approvals/{approval_id}/approve_once`
- Deny: `POST /v1/approvals/{approval_id}/deny`
- Approve For Session: `POST /v1/approvals/{approval_id}/decisions` with
  `scope=session`
- Approve For Agent: `POST /v1/approvals/{approval_id}/decisions` with
  `scope=agent`

Draft-only local action:

- Other: captures a local draft response for future modified approval support.

Navigation actions:

- More Info: opens a request metadata and redacted payload drill-down.
- Open TUA Session: opens the TUA prototype with approval context.
- Open TUI Session: opens the TUI prototype with approval context.

Planned or disabled actions:

- Approve Forever
- Pause Agent
- Stop Task
- Stop Agent

Permanent policy enforcement and real intervention execution remain out of
scope for this slice. The UI marks those actions as planned instead of showing
fake success.

## Backend Gap Review

Current backend support:

- `once`, `session`, `agent`, and `permanent` scope values are accepted by the
  approval decision schema.
- `decision_scope` is persisted.
- Approval decision audit events are written.
- `approval.resolved` events include the selected scope.

Known backend gaps:

- Permanent approvals are not enforced as policy.
- Modified/conditional approval payloads are not implemented.
- Intervention endpoints are placeholder-only and do not pause or stop agents.
- The inner `ApprovalDecisionRequest.signature` field is not independently
  verified; the enclosing HTTP request is authenticated with device signing.

## Demo Flow

Start the local demo gateway:

```bash
uv run --project gateway python gateway/scripts/mobile_realness_demo.py --port 8787
```

Then:

1. Run the Flutter app.
2. Set the gateway URL to `http://127.0.0.1:8787/v1`.
3. Pair the app from Settings.
4. Open Home or Inbox and verify live status.
5. Open an approval and submit a signed once/session/agent decision.
6. Verify the gateway emits `approval.resolved` and records an audit event.

## Screenshots

Updated screenshots are stored under:

```text
docs/implementation/screenshots/mobile-alpha/
```

Expected capture set:

- `home-live.png`
- `inbox-live.png`
- `approval-detail-live.png`
- `approval-more-actions.png`
- `tua-from-approval.png`
- `tui-from-approval.png`
