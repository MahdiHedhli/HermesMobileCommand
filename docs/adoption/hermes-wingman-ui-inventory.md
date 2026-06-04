# Hermes Wingman UI/UX Inventory

## Purpose

This inventory identifies hermes-wingman screens and patterns worth reusing, adapting, or using only as inspiration for Hermes Mobile Control Plane.

Roadmap phase mapping:

- **P1**: Read-only observer
- **P2**: Chat
- **P3**: Approvals
- **P4**: Multi-agent registry
- **P5**: Intervention
- **P6**: Voice

## Screen Inventory

| Wingman Screen / Path | What It Does | Relevance | MVP Phase Mapping | Adoption Note |
| --- | --- | --- | --- | --- |
| Dashboard `lib/screens/dashboard/dashboard_screen.dart` | Health/status grid, quick actions, recent sessions, cron, gateway status | High | P1, P3, P4, P5 | Adapt into global node/agent dashboard with pending approvals, security alerts, emergency stop |
| Chat `lib/screens/chat/chat_screen.dart` | Tabbed chat, streaming, local session management, resume session | High | P2 | Adapt chat layout and streaming UX; add node/agent/session context and approval banners |
| Sessions `lib/screens/sessions/sessions_screen.dart` | Search/filter session list, stats, selected session detail | High | P1, P2, P5 | Adapt as session browser and live activity entry point; namespace by node/agent |
| Logs `lib/screens/logs/logs_screen.dart` | Auto-poll logs, level filter, keyword filter, auto-scroll | High | P1, P5 | Adapt for live activity/log tab; add redaction, WebSocket/backfill, node scoping |
| Models `lib/screens/models/models_screen.dart` | Model lists, favorites, current model, probe status, switching | Medium | P1 context only | Use as read-only model/provider status inspiration; avoid provider mutations in MVP |
| Skills `lib/screens/skills/skills_screen.dart` | Search skills and toggle enabled state | Medium | P1, P5 | Adapt read-only skills visibility; toggles require approvals later |
| Memory `lib/screens/memory/memory_screen.dart` | List/search/delete memory entries | Medium | P1, P5 | Adapt read/search with redaction; delete requires approval |
| Files `lib/screens/files/files_screen.dart` | System-wide file browser, view/edit/rename/delete/open | Low for direct use | P2 artifact viewing, P5 gated actions | Reject direct file manager; adapt only safe artifact viewer and read-only file metadata |
| Gateway `lib/screens/gateway/gateway_screen.dart` | Gateway running status, connected platforms, start/stop | Medium | P1, P4, P5 | Adapt gateway health/platform status; start/stop must be signed intervention |
| Gateway Setup `lib/screens/gateway/gateway_setup_screen.dart` | Configure messaging platforms and secrets | Low | Later admin, not MVP | Inspiration only; raw secret entry from mobile is out of scope |
| Cron `lib/screens/cron/cron_screen.dart` | List scheduled jobs | Medium | P1, P4 | Adapt scheduled task visibility; job run/toggle requires approval |
| Missions `lib/screens/missions/missions_screen.dart` | Local mission create/run/status | Medium | P4, P5 | Use vocabulary for task/mission records; reject direct run model |
| Profiles `lib/screens/profiles/profiles_screen.dart` | Model/config presets | Low | Later | Defer; profile apply is config mutation |
| Providers `lib/screens/providers_screen.dart` | Provider auth/key actions | Low | Not MVP | Reject for mobile control plane; read-only status only if needed |
| Config `lib/screens/config/config_screen.dart` | YAML editor | Low | Not MVP | Reject direct edit; possible redacted config summary only |
| Tools / CLI Tools `lib/screens/tools/*` | Diagnostics and Hermes CLI wrappers | Medium | P1 diagnostics, P5 interventions | Adapt safe diagnostics; reject generic command execution |
| Setup Wizard `lib/screens/setup/setup_wizard_screen.dart` | Install/configure Hermes | Low | Not MVP | Do not adopt for mobile app; setup stays local/admin |

## Navigation Patterns

| Pattern | Source | Use In HermesMobileCommand |
| --- | --- | --- |
| Persistent desktop sidebar | `lib/widgets/main_shell.dart` | Not relevant to native mobile MVP except as information architecture reference |
| Mobile bottom nav | `lib/widgets/main_shell.dart` | Adapt, but replace with Dashboard, Agents, Activity, Approvals, Notifications, Voice, Settings |
| Backend status dot | `lib/widgets/backend_status_dot.dart` | Adopt/adapt for per-node gateway status |
| Quick action cards | Dashboard | Adapt for node health, pending approvals, blocked tasks, emergency controls |
| Search/filter list screens | Sessions, Skills, Memory, Logs | Adapt for agent/session/approval/log lists |
| Polling logs | Logs | Replace primary polling with WebSocket event stream and REST backfill |
| Confirm dialogs | Chat delete, file delete, gateway stop | Adapt only when paired with signed approval/intervention semantics |

## Theme And Widget Patterns

| Pattern | Source | Recommendation |
| --- | --- | --- |
| Tokenized color scheme | `lib/theme/app_theme.dart` | Inspire a restrained mobile design token system |
| Glass cards/backdrop blur | `lib/theme/glass_card.dart` | Avoid as dominant visual style; mobile control plane should be dense and utilitarian |
| Animated background/starfield | `lib/theme/animated_background.dart` | Reject for MVP; harms operational clarity |
| Status chips/cards | Various screens | Adapt for node/agent/session/approval status |
| Reusable navigation button widgets | `lib/widgets/*` | Inspire component organization if Flutter is chosen |

## MVP Mapping

### Phase 1: Read-Only Observer

Useful Wingman references:

- Dashboard status grid
- Sessions screen
- Logs screen
- Gateway screen status
- Skills/memory read-only screens
- Backend status dot

Required product changes:

- Add node/agent context.
- Redact sensitive logs/memory.
- Replace LAN discovery with Tailscale pairing.
- Use event stream/backfill rather than only polling.

### Phase 2: Chat

Useful Wingman references:

- Chat tab/session UX
- SSE streaming behavior as reference
- ChatManager persistence pattern

Required product changes:

- Use authenticated gateway API.
- Tie messages to node/agent/session.
- Support push deep links and approval banners.
- Avoid GET query messages for streaming.

### Phase 3: Approvals

Wingman gap:

- No approval queue, signed decisions, approval states, or push approval flow found.

New design required:

- Approval queue
- Approval detail
- Signed decision controls
- Push notification deep links
- Audit trail

### Phase 4: Multi-Agent

Useful Wingman references:

- Dashboard aggregation
- Gateway/platform inventory
- Mission/task vocabulary

Required product changes:

- Multi-node registry.
- Agent tags/environments/capabilities.
- Node-scoped IDs.
- Global activity dashboard.

### Phase 5: Intervention

Useful Wingman references:

- Gateway stop/start confirmation pattern
- Logs/session context
- Tools diagnostics vocabulary

Required product changes:

- Signed intervention requests.
- Pause, kill task, kill agent, quarantine agent.
- Browser/session takeover only where supported.
- Audit every intervention.

### Phase 6: Voice

Wingman gap:

- No reusable voice mobile UX pattern found in inspected screens.

New design required:

- Push-to-talk screen.
- Voice session lifecycle.
- Transcript and confirmation phrase UI.
- Voice callback notifications.

## Screens To Build First In HermesMobileCommand

1. Dashboard from scratch, inspired by Wingman status grid.
2. Agent/session list from scratch, inspired by Wingman Sessions.
3. Live activity/logs from scratch, inspired by Wingman Logs.
4. Chat from scratch or heavily adapted, inspired by Wingman Chat.
5. Approval queue and detail from our own architecture; Wingman has no equivalent.
