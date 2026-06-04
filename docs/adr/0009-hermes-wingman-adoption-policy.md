# ADR-0009: Hermes Wingman Adoption Policy

## Status

Accepted

## Date

2026-06-04

## Context

`hermes-wingman` is a Flutter + Rust + Rails GUI for Hermes Agent with desktop, mobile, and web surfaces. It includes useful patterns for dashboards, chat, sessions, logs, models, skills, memory, files, cron, gateway, missions, backend endpoints, and build structure.

HermesMobileCommand has a different mission: a Tailscale-first mobile control plane focused on secure mobile access, push notifications, approval queues, multi-agent control, live intervention, and eventual voice mode.

## Decision

Use hermes-wingman as a reference implementation and selective source of reusable Apache-2.0 components, but do not fork it wholesale.

## Accepted Reuse Categories

- Feature taxonomy for Hermes GUI surfaces.
- Read-only model ideas for sessions, logs, skills, memory, gateway status, and missions/tasks.
- UX inspiration for dashboard, chat, session list, logs, and backend status indicators.
- Endpoint taxonomy for comparing ordinary GUI APIs against our control-plane APIs.
- Build/test category inspiration.
- Small implementation fragments only after explicit license and security review.

## Rejected Reuse Categories

- LAN scanning and auto-discovery.
- Permissive CORS or unauthenticated gateway APIs.
- Direct provider API calls from the mobile-facing backend.
- Raw provider API key or OAuth administration from mobile MVP.
- Raw config YAML editing from mobile.
- Broad file browser, absolute filesystem access, recursive delete, or direct file writes.
- Generic Hermes CLI proxy endpoints.
- Setup/install workflows from mobile.
- Direct service start/stop controls without signed intervention and audit.
- Full GUI replacement scope.

## Security Constraints

Any copied or adapted pattern must preserve HermesMobileCommand requirements:

- Tailscale-first private connectivity.
- Explicit pairing before trust.
- Device-bound session tokens.
- Signed approvals and signed emergency interventions.
- Approval replay protection.
- Secret-free push notifications.
- Redacted event streams and logs.
- Node/agent/session scoping.
- Append-only audit logging.
- Fail-closed policy for consequential actions.

## License Handling

The upstream `LICENSE` file is Apache-2.0. The README badge says MIT, but the license file is authoritative unless upstream clarifies.

If code is copied:

- Preserve Apache-2.0 license text in third-party notices.
- Preserve upstream copyright and attribution notices.
- Mark modified files as modified.
- Record copied files/functions in the adoption matrix or a follow-up review note.
- Confirm whether a source `NOTICE` file exists at the reviewed commit; none was found in this audit.

## Future Review Gate

Before copying any hermes-wingman code into HermesMobileCommand:

1. Identify exact upstream files/functions and commit hash.
2. Classify the component as ADOPT or ADAPT in the adoption matrix.
3. Document why design-only reuse is insufficient.
4. Run security review for auth, transport, secret handling, file access, CLI execution, logs, redaction, and audit behavior.
5. Add Apache-2.0 attribution handling.
6. Confirm no rejected assumptions are imported.

## Consequences

Positive:

- We benefit from Wingman's Hermes surface inventory and UI/backend lessons.
- Product direction remains mobile safety/control plane.
- Security posture stays stronger than LAN-first GUI replacement.

Negative:

- Direct reuse is limited.
- Teams must rebuild many useful screens around stricter control-plane contracts.
- Any code copying requires process overhead.
