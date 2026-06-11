# Technical Debt Review

Sprint: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`

## Scope

Reviewed:

- Gateway route structure
- Gateway storage structure
- Mobile repositories and view models
- OpenAPI surface
- Event model
- Security-sensitive operator capability paths

This is an architecture debt review, not a production code change request.

## High Priority

### Gateway route monolith

Evidence:

- `gateway/src/hermes_gateway/app.py` is over 2,000 lines and contains health, pairing, approvals, notification, TUI, TUA, browser assistance, voice, and helper logic.

Risk:

- Route-specific security checks are harder to audit.
- Adding beta-grade intervention paths will increase coupling.
- Shared lifecycle behavior is duplicated in route handlers.

Recommendation:

- Split into routers: `pairing`, `devices`, `approvals`, `notifications`, `events`, `tui`, `tua`, `browser_assistance`, `voice`, and `health`.
- Keep shared signed-device dependencies and audit helpers in a common module.

### Store class is too broad

Evidence:

- `gateway/src/hermes_gateway/store.py` is over 1,700 lines and owns schema creation, row conversion, and all entity operations.

Risk:

- Schema changes are harder to review.
- Entity-specific lifecycle rules can drift.
- Tests can become broad integration tests instead of focused storage tests.

Recommendation:

- Introduce store modules or repository classes by domain.
- Move schema constants/migrations into their own module.
- Keep SQLite as the storage engine for now; the debt is shape, not database choice.

### Capability grants need management UX

Evidence:

- Runtime Integration 007 added a `capability_grants` table and centralized capability checks.
- Device permissions still coexist with capability grants for compatibility.
- There is no mobile/operator UX yet to review, revoke, or explain grants.

Risk:

- Operators may not understand why a runtime-created TUA/browser/voice request was allowed or denied.
- Grant revocation remains a backend concern rather than a visible safety workflow.

Recommendation:

- Add signed mobile grant review and revocation screens before beta.
- Show failed capability checks in Agent Detail and audit views.
- Preserve the centralized helper as the single enforcement path.

### Operator session lifecycle duplicated

Evidence:

- TUI, TUA, browser assistance, and voice all model session creation, state changes, events, audit, and closure separately.

Risk:

- State names and event types will drift.
- Home, Inbox, Missions, and Agent Detail need a common summary model.

Recommendation:

- Add an `OperatorSession` projection and shared lifecycle event helper.
- Keep subtype-specific route behavior and transport logic separate.

## Medium Priority

### Event type strings need centralization

Risk:

- Mobile stream handling can silently miss new or renamed events.

Recommendation:

- Define event type constants and a typed gateway event envelope.
- Add OpenAPI/schema examples for each event family.

### Mobile mock and gateway models overlap

Risk:

- Alpha models can drift from gateway-backed core models.
- UX screens may accidentally rely on mock-only fields.

Recommendation:

- Keep mock repositories, but convert them to emit core platform models where possible.
- Use explicit demo-only fixture mappers for screens still ahead of the backend.

### Mission is under-modeled in the gateway

Risk:

- The UI uses missions as first-class work context, but backend contracts still lean on sessions, approvals, and events.

Recommendation:

- Add durable Mission schema before expanding mission management.
- Map Hermes sessions/tasks into Mission consistently.

### OpenAPI mixes foundation and advanced surfaces

Risk:

- Consumers may treat prototype surfaces as production-ready.

Recommendation:

- Add `x-hmcp-stage` or explicit descriptions for `dev-only`, `alpha`, and `beta-candidate` endpoints.
- Keep TUI local PTY marked development-only.

### Native secure storage is platform-aware but not native-validated

Risk:

- Chrome/web validation does not prove iOS Keychain or Android Keystore behavior.

Recommendation:

- Complete iOS and Android toolchain setup.
- Add target-specific secure storage tests once native SDKs are available.

## Low Priority

### Screen naming abbreviations

Risk:

- TUA/TUI are concise for the project but less clear to new operators.

Recommendation:

- Use expanded screen subtitles: "Assistance" and "Terminal" while keeping TUA/TUI in technical docs.

### Notification categories and inbox type colors

Risk:

- Attention items may blur together during demos.

Recommendation:

- Add consistent icons and colors for approvals, security alerts, assistance, voice callbacks, and system health.

### Documentation now has both old and new roadmap docs

Risk:

- New engineers may read the feature-slice roadmap first.

Recommendation:

- Keep `docs/roadmap.md` as historical build-slice plan.
- Treat `docs/roadmap-next.md` as the current platform roadmap and link it prominently from `docs/README.md`.

## Migration Risks

- Consolidating operator sessions too aggressively could weaken route-specific authorization.
- Promoting policy proposals into active policies before revocation UX exists would violate fail-closed assumptions.
- Moving from SQLite before beta would add migration work without solving the current product coherence issues.
- Native validation may reveal package or platform API mismatches that are invisible on Chrome.

## Recommended Order

1. Split gateway routers and storage domains.
2. Add `OperatorSession` projection and common event/audit helpers.
3. Promote `CapabilityGrant` to explicit policy model.
4. Canonicalize Mission in the gateway.
5. Add endpoint maturity labels to OpenAPI.
6. Complete native secure storage validation on iOS and Android.
