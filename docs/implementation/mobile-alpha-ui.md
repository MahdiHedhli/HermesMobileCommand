# Mobile Alpha UI

Sprint: `HERMES-MCP-MOBILE-ALPHA-UI-001`

This slice creates the first clickable Flutter alpha for Hermes Mobile Control Plane. The goal is visible product shape, not backend expansion.

## Scope

Implemented alpha screens:

- Home: fleet metrics, pending approvals, active missions, agent fleet, recent activity.
- Agents: searchable fleet list with team filters, optional grouping, and agent detail navigation.
- Agent detail: status, node, mission, capabilities, notification count, approval count, and TUA/TUI entry points.
- Inbox: unified notifications, approvals, assistance requests, security alerts, unread markers, and filters.
- Approval detail: risk summary, redacted payload, constraints, primary approve/deny actions, and expanded More action sheet.
- TUA: operator assistance timeline, user replies, assistance state, and return-to-agent action.
- TUI: terminal scrollback prototype, copy action, and four-page keyboard accessory bar.
- Missions: mission list with status, progress, and TUA/TUI entry points.
- Voice: reserved future surface for push-to-talk, half-duplex, and full-duplex phases.
- Settings: gateway profile, device trust, and safety defaults.

Out of scope for this slice:

- APNs and FCM.
- Voice streaming.
- Browser control.
- Terminal PTY execution.
- Real approval execution from the Flutter UI.

## UI Architecture

The alpha is organized around explicit model, repository, and viewmodel layers:

- `mobile/lib/src/models/alpha_models.dart`
- `mobile/lib/src/repositories/alpha_repository.dart`
- `mobile/lib/src/repositories/mock_alpha_repository.dart`
- `mobile/lib/src/repositories/gateway_alpha_repository.dart`
- `mobile/lib/src/viewmodels/alpha_viewmodels.dart`
- `mobile/lib/src/widgets/alpha_components.dart`

Widgets consume viewmodels and repository abstractions instead of reaching directly into gateway APIs. The launch route uses `MockAlphaRepository` so a developer can open the app without a running gateway. `GatewayAlphaRepository` adapts gateway-backed repositories for agents, missions, approvals, notifications, and dashboard data. Later slices added dedicated gateway repositories for TUI, TUA, browser assistance, advanced approval responses, and text-backed voice, while mock fallbacks remain for unpaired alpha use.

## Interaction Notes

Approval detail intentionally presents a compact primary path:

- Approve
- Deny
- More

The More sheet includes the larger intervention vocabulary:

- Approve Once
- Approve For Session
- Approve For Agent
- Approve Forever
- Other
- More Info
- Open TUA Session
- Open TUI Session
- Pause Agent
- Stop Task
- Stop Agent

The TUI keyboard accessory is non-functional by design in this slice. It establishes the mobile control feel and reserves layout for:

- Page 1: ESC, TAB, CTRL, ALT, CMD, directional keys.
- Page 2: `/`, `~`, `|`, `&`, `$`, `;`, `:`.
- Page 3: `{}`, `[]`, `()`, `<>`.
- Page 4: F1-F12, Home, End, PgUp, PgDn.

## Design Direction

The visual target is a quiet operations console: dark graphite surfaces, compact cards, status pills, high-signal lists, and restrained green, amber, red, and blue accents. The app avoids a Slack-like channel metaphor and keeps approvals, fleet status, and intervention actions central.

## Validation

Flutter SDK was not available in the local environment during implementation, so `flutter analyze`, `flutter test`, and screenshot capture were skipped.

Fallback validation performed:

- Dart relative import resolution.
- `git diff --check`.
- Repo hygiene scan for `.DS_Store`.

## TestFlight Gaps

Before TestFlight-quality validation:

- Install Flutter SDK and run `flutter analyze` and `flutter test`.
- Add widget tests for Home, Inbox, Approval detail, TUA, and TUI accessory pages.
- Bind `GatewayAlphaRepository` through a real gateway configuration flow.
- Implement platform secure storage for mobile device keys.
- Add signed mobile request execution for approval decisions.
- Generate screenshots on iOS and Android simulators.
