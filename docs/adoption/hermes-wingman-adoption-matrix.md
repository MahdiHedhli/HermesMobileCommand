# Hermes Wingman Adoption Matrix

Audit ID: `HERMES-WINGMAN-ADOPTION-AUDIT-001`

Repository reviewed: `https://github.com/synthalorian/hermes-wingman`

Clone location used for audit: `/tmp/hermes-wingman-audit.PacR25`

Commit reviewed: `da7246e218a32152426977a5a0e41669c9d05ba4`

## Classification Definitions

- **ADOPT**: Reuse the pattern with minimal product change. Code copy may still require license handling and a security review.
- **ADAPT**: Useful but must be changed substantially for Tailscale-first mobile control-plane needs.
- **INSPIRE**: Good reference for product shape, UX, or naming, but design-only for this project.
- **REJECT**: Do not use directly because it conflicts with Hermes Mobile Control Plane direction or security requirements.

## License Review

| Item | Finding |
| --- | --- |
| License type | Apache License 2.0 in `LICENSE` |
| README mismatch | README badge says MIT, but repository `LICENSE` is Apache-2.0; treat `LICENSE` as authoritative unless upstream clarifies |
| NOTICE file | No source-level `NOTICE` file found; only a generated Flutter `dist/.../NOTICES.Z` artifact exists |
| Direct code reuse | Legally acceptable under Apache-2.0 if we preserve license, attribution notices, and mark modified files |
| Patent grant | Apache-2.0 includes a patent grant subject to its termination clause |
| Required handling if code is copied | Add Apache-2.0 attribution to copied files, include upstream LICENSE in third-party notices, preserve copyright/attribution notices, document modifications, and run a security review before merge |
| Recommended posture | Use as reference implementation first. Copy code only after explicit review gate and written note in this matrix or a follow-up ADR |

## Adoption Matrix

| Component / Path | Purpose | Classification | Rationale | Security Notes | Required Changes Before Use | Code Copy |
| --- | --- | --- | --- | --- | --- | --- |
| `README.md` product catalog | Defines Wingman as full GUI replacement across desktop/mobile/web | INSPIRE | Useful feature inventory for Hermes surfaces, but product goal differs | README promotes LAN access and GUI replacement; our direction is Tailscale-first safety/control plane | Keep only surface inventory; do not adopt product positioning | Design-only |
| `LICENSE` | Apache-2.0 license | ADOPT | Compatible permissive license with attribution and patent grant | README license badge mismatch must be documented | Preserve license and attribution if copying code | Copy allowed with Apache-2.0 handling |
| `lib/models/hermes_models.dart` | Dart models for sessions, status, logs, skills, memory, files, gateway platforms | ADAPT | Useful schema hints for Hermes state surfaces | Does not include node/device/security scopes needed by Mobile Control Plane | Add `node_id`, `agent_id`, approval, notification, audit, voice, and redaction fields | Copy allowed only after model redesign |
| `lib/services/hermes_api_client.dart` typed client methods | Mobile/desktop client wrapper around backend API | ADAPT | Useful service abstraction and backend status handling | Uses plain HTTP, no device auth, no signed approvals, LAN discovery | Replace transport/auth with Tailscale URL registry, device tokens, signed approval calls, event stream | Design preferred; code copy gated |
| `lib/services/hermes_api_client.dart` LAN discovery | Scans local subnet hosts on port `9120` | REJECT | Conflicts with Tailscale-first, explicit pairing, and no-scanning posture | LAN scanning can surprise users, trigger network alarms, and discover rogue hosts | Replace with explicit pairing, Tailscale node URL entry, QR/code enrollment | Do not copy |
| `lib/services/hermes_api_client.dart` backend process start | Desktop app starts Rust backend process | REJECT | HermesMobileCommand is mobile-first and should not launch desktop backend binaries | Sets `BIND_ADDR=0.0.0.0:9120`, but backend code currently binds `127.0.0.1:9120`; mismatch is unsafe/confusing | Mobile app should never start host services; gateway installed beside Hermes | Do not copy |
| `lib/services/hermes_client.dart` direct desktop Hermes client | Runs CLI, reads config/logs/files locally | INSPIRE | Shows useful Hermes adapter operations | Direct filesystem/CLI access is not valid on mobile and bypasses approval policy | Move equivalent operations into gateway adapters with auth, policy, redaction, audit | Design-only |
| `lib/services/chat_manager.dart` | Local chat session state and persistence | ADAPT | Useful for mobile UI state and offline draft handling | Local persistence must avoid storing sensitive content unencrypted | Use secure or encrypted storage; bind cached data to node/device; add redaction | Copy allowed only after storage review |
| `lib/services/wingman_settings.dart` | App settings and backend URL dialog | ADAPT | Backend connection dialog maps to node settings UX | Stores connection settings locally without pairing/device trust semantics | Replace host/port with node registry, fingerprint, Tailscale URL, device status | Design-only |
| `lib/screens/dashboard/dashboard_screen.dart` | Status grid, quick actions, recent activity | ADAPT | Strong candidate for Phase 1 dashboard layout concepts | Needs multi-node, pending approval, emergency stop, and security alert emphasis | Reframe as control-plane dashboard, not general GUI landing | Design-only or selective UI ideas |
| `lib/screens/chat/chat_screen.dart` | Tabbed chat with streaming and session resume | ADAPT | Useful Phase 2 mobile chat pattern | No approval context or node scoping; local history sensitivity | Add node/agent/session headers, event cursor, redaction, push-deep-link context | Design-only unless Flutter chosen |
| `lib/screens/sessions/sessions_screen.dart` | Searchable session list/detail | ADAPT | Useful Phase 1/2 session browser | Session IDs are not node-scoped in UI | Namespace by node and agent; add live activity and approval badges | Design-only |
| `lib/screens/logs/logs_screen.dart` | Polling logs view with level/keyword filters | ADAPT | Good Phase 1 observer and Phase 5 intervention support | Logs may expose secrets; polling every 3s is less ideal than event stream | Add redaction, event stream/backfill, severity audit links, node scoping | Design-only |
| `lib/screens/models/models_screen.dart` | Model catalog, favorites, probe, switch | INSPIRE | Model visibility is useful but not core differentiator | Direct provider probing/API keys not aligned with Hermes-mediated control | Treat as read-only Hermes capability/status, not direct provider management | Design-only |
| `lib/screens/providers/providers_screen.dart` | Provider auth/key management | REJECT | Pulls product toward full GUI/config replacement | Handles API keys and OAuth flows through mobile-accessible backend | Keep provider actions inside Hermes/web admin; mobile should not manage raw keys in MVP | Do not copy |
| `lib/screens/config/config_screen.dart` | YAML config editor | REJECT | Conflicts with safety-scoped mobile control plane | Direct config editing from mobile is high risk | Offer read-only config summaries or targeted safe settings only | Do not copy |
| `lib/screens/skills/skills_screen.dart` | Skills browser/toggle | ADAPT | Skills visibility is in our web parity scope | Toggle actions can alter agent behavior and need approval/audit | Make read-only in early phases; gate toggles behind signed approval | Design-only |
| `lib/screens/memory/memory_screen.dart` | Memory viewer/search/delete | ADAPT | Memory visibility maps to web parity | Memory content may be sensitive; delete is consequential | Read-only with redaction first; delete requires approval/audit | Design-only |
| `lib/screens/files/files_screen.dart` | System-wide file explorer with read/edit/delete/rename | REJECT | Direct file management is outside mobile safety scope | Backend allows absolute paths and recursive delete; high risk | Replace with artifact viewer and approval-gated file actions scoped to Hermes sessions | Do not copy |
| `lib/screens/gateway/gateway_screen.dart` | Gateway status and service toggle | ADAPT | Platform status ideas useful for Hermes node/gateway health | Start/stop service from mobile requires signed intervention and audit | Keep status; gate service controls behind emergency/intervention framework | Design-only |
| `lib/screens/gateway/gateway_setup_screen.dart` | Configure messaging gateway platforms | INSPIRE | Platform status/setup inventory useful as reference | Writes tokens/secrets into `.env`; not a mobile control-plane MVP | Keep out of MVP; future admin surface needs secret-safe workflow | Design-only |
| `lib/screens/cron/cron_screen.dart` | Cron job visibility | INSPIRE | Scheduled task visibility maps to live activity/agent state | Running/toggling jobs can be consequential | Read-only scheduled task status first; actions require approval | Design-only |
| `lib/screens/missions/missions_screen.dart` | Mission definitions and run controls | INSPIRE | Mission/task concept maps to multi-agent control plane | Stores prompts locally and runs `hermes -z`; no approval gate | Use as vocabulary input for task records; do not adopt run model | Design-only |
| `lib/screens/profiles/profiles_screen.dart` | Model/config presets | INSPIRE | Profiles may inform capability presets | Applying presets changes config/behavior | Defer; not core safety-control MVP | Design-only |
| `lib/screens/tools/*` and CLI tools | Hermes CLI status/tools panels | INSPIRE | Some diagnostics useful for node detail | CLI proxy endpoints can expose sensitive output and unsafe commands | Replace with explicit safe diagnostics endpoints | Design-only |
| `lib/widgets/main_shell.dart` | Persistent desktop sidebar and mobile bottom nav | ADAPT | Navigation pattern useful; screen list is comprehensive | Current mobile nav omits approvals/emergency controls | Rebuild nav around Dashboard, Agents, Activity, Approvals, Notifications, Voice, Settings | Design-only |
| `lib/widgets/backend_status_dot.dart` | Compact backend status indicator | ADOPT | Simple useful status pattern for node connectivity | Must be node-specific and accessible | Adapt text to node/gateway status and Tailscale reachability | Code copy allowed if Flutter chosen and attributed |
| `lib/theme/*`, `lib/widgets/*` theme system | 29 themes, glass cards, animated backgrounds | INSPIRE | Theming system shows reusable design organization | Decorative visual style is not priority and may hurt mobile utility | Use quiet utility UI; borrow tokenized theme idea only | Design-only |
| `backend/openapi.yaml` | Wingman REST API contract | ADAPT | Endpoint inventory helps API lessons | Lacks auth, approvals, device trust, push, multi-node, audit | Compare against our gateway OpenAPI; do not import wholesale | Design-only |
| `backend/src/main.rs` route layout | Axum route composition | ADAPT | Clean enough route inventory for gateway service map | Permissive CORS and no auth middleware; many unsafe write endpoints | Add auth, device middleware, signed approvals, scoped APIs, audit | Code copy gated |
| `backend/src/main.rs` CORS | `CorsLayer::permissive()` | REJECT | Not acceptable for mobile control plane | Any origin can call APIs if reachable | Use explicit origins or app-authenticated API; Tailscale is not enough | Do not copy |
| `backend/src/main.rs` bind behavior | Binds `127.0.0.1:9120`; README claims LAN/`0.0.0.0` | ADAPT | Bind default should be safe localhost; docs mismatch is useful caution | Mobile LAN flow may not work as README describes unless code changes | Use explicit configured bind; default Tailscale/private interface only | Design-only |
| `backend/src/handlers/files.rs` | File list/read/write/delete/rename/mkdir | REJECT | Direct absolute-path filesystem API conflicts with safety model | Allows navigation outside `~/.hermes`, full read/write/delete recursively | Replace with artifact/session-scoped file access and approval-gated actions | Do not copy |
| `backend/src/handlers/cli.rs` | Generic Hermes CLI command proxy and many CLI wrappers | REJECT | Too broad for secure mobile gateway | Can expose outputs from security, secrets, dump, debug, backup, plugins, etc. | Replace with explicit allowlisted diagnostics and policy-gated interventions | Do not copy |
| `backend/src/handlers/config.rs` | Config read/write/update and model override | REJECT for write, ADAPT for read | Read-only config summary useful; raw writes are unsafe | Writes full config and does string patching | Provide redacted read-only config summary; any mutation requires approval | Design-only |
| `backend/src/handlers/chat_stream.rs` | SSE chat stream and provider/CLI fallback | ADAPT | Streaming chat pattern useful for Phase 2 | Direct provider calls and GET query message leak are unsafe | Use authenticated WebSocket/events; POST for messages; Hermes-mediated actions | Design-only |
| `backend/src/chat.rs`, provider calls | Direct provider HTTP calls and model routing | REJECT | HermesMobileCommand should not call providers directly | API keys may be read from config and used by gateway GUI | Keep provider use inside Hermes runtime | Do not copy |
| `backend/src/handlers/auth.rs` | Provider OAuth/API key management | REJECT | This is provider auth, not mobile device auth | API key passed to backend/CLI; stdout/stderr returned | Implement device pairing/auth separately; do not expose provider keys | Do not copy |
| `backend/src/handlers/gateway.rs` platform metadata | Messaging platform metadata/status | INSPIRE | Useful inventory of gateway surfaces | Secret `.env` editing and service controls are unsafe | Use read-only gateway/platform status in node detail; safe setup elsewhere | Design-only |
| `backend/src/handlers/gateway.rs` env writer | Saves tokens/secrets to `~/.hermes/.env` via `/tmp/save_env.py` | REJECT | Not acceptable for mobile control plane | Writes secrets from mobile-accessible endpoint; temp helper script | No mobile raw secret entry in MVP | Do not copy |
| `backend/src/handlers/setup.rs` install/autoconfigure | Installs Hermes and writes config | REJECT | Setup wizard is GUI replacement, not mobile safety plane | Runs remote install script, pip/brew, and config writes | Keep setup outside mobile app or local admin-only | Do not copy |
| `backend/src/handlers/memory.rs` | Memory list/search/delete | ADAPT | Read/search useful for parity | Delete requires approval; content needs redaction | Read-only first; approval-gated mutation | Design-only |
| `backend/src/handlers/skills.rs` | Skill list/toggle/version/update | ADAPT | List/version useful; toggle/update are consequential | Skill toggle/update can change behavior | Read-only first; mutation requires signed approval | Design-only |
| `backend/src/handlers/metrics.rs` | Basic gateway metrics/restart | ADAPT | Health/metrics useful | Restart is not implemented, but future controls need audit | Expand into health snapshots; intervention-gate restart | Design-only |
| `backend/src/platform.rs` | Hermes home/binary discovery and `run_hermes` helper | ADAPT | Useful for gateway adapter design | Generic command execution must not be exposed to mobile | Wrap in allowlisted Hermes adapter with audit and policy | Code copy gated |
| `backend/src/helpers.rs` | Config/model/provider helpers | INSPIRE | Some parsing and catalog ideas useful | Provider catalog can drift; reads secrets/config | Use only as reference for Hermes metadata adapter | Design-only |
| `web/` Rails app | Web dashboard proxy and GUI screens | INSPIRE | Useful for web parity inventory and metadata models | Rails app has no app auth model in inspected controller base; proxies unsafe backend APIs | Do not add web dashboard scope to mobile project | Design-only |
| `web/app/models/*` | Mission, profile, webhook, cached memory/skills, usage snapshots | ADAPT | Data ideas useful for tasks, capabilities, usage | Webhook secrets and profiles need security review | Adapt only task/memory/skill metadata; avoid webhook admin scope | Design-only |
| `web/app/controllers/files_controller.rb` | Rails file browser | REJECT | Direct file read/write under `~/.hermes` from web | Path handling needs traversal review and lacks mobile approval model | Do not adopt; use scoped artifact viewer | Do not copy |
| `docs/plans/2026-05-25-wingman-webapp-architecture.md` | Wingman web/Rails architecture plan | INSPIRE | Good inventory of screens/endpoints/data models | Plans include GUI replacement and direct file/config operations | Use as feature taxonomy only | Design-only |
| `build.sh`, `build_macos.sh`, `build_windows.ps1` | Cross-platform build scripts | INSPIRE | Useful packaging reference if Flutter/Rust chosen | Scripts deploy to local bin and package desktop app; not relevant to mobile-first | Do not adopt until stack chosen | Design-only |
| `.github/workflows/ci.yml` | CI for Rust, Flutter, Rails | INSPIRE | Shows desired checks: cargo fmt/clippy, flutter analyze, Brakeman/RuboCop | Paths appear inconsistent with current `web/` directory (`hermes_wingman_web` references) | Build our own CI after stack decision | Do not copy |
| `test/widget_test.dart`, `web/test/*` | Minimal smoke/fixture tests | INSPIRE | Confirms basic test layout only | Coverage is shallow; no security tests | Build dedicated tests for auth, approval, redaction, event stream | Design-only |

## Summary Counts

| Classification | Count | Meaning For HermesMobileCommand |
| --- | ---: | --- |
| ADOPT | 2 | License handling and small status-indicator pattern only |
| ADAPT | 19 | Useful structures requiring security/product reshaping |
| INSPIRE | 17 | Feature taxonomy, UX ideas, and planning references |
| REJECT | 16 | Unsafe or off-direction direct reuse |

## Recommended First Adaptations

1. Session, status, log, skill, memory, and gateway platform model ideas from `lib/models/hermes_models.dart`.
2. Dashboard/session/log UX patterns, rewritten around node/agent/approval context.
3. Backend endpoint taxonomy from `backend/openapi.yaml`, compared against our gateway API.
4. Gateway platform health/status inventory, read-only and node-scoped.
5. Mission/task vocabulary for future multi-agent task records, not the direct execution model.

## Direct Copy Policy

No hermes-wingman source code was copied into HermesMobileCommand during this audit. Future direct copying is allowed only when all are true:

- The component is classified ADOPT or ADAPT.
- A follow-up review names the exact files/functions to copy.
- Apache-2.0 license and attribution handling is added.
- Security review confirms the copied code does not preserve unsafe LAN, auth, file, config, CLI, or secret-handling assumptions.
