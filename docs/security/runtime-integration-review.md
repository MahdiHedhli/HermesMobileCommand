# Runtime Integration Security Review

Sprint: `HERMES-MCP-REAL-HERMES-CLIENT-008`

## Summary

The real Hermes client path preserves the existing security posture: runtime calls are loopback-first, mobile decisions remain signed by paired devices, and operator handoffs stay auditable. The new client improves integration ergonomics but does not grant runtime callers authority to approve their own actions.

## Findings

| Area | Finding | Risk | Recommendation |
| --- | --- | --- | --- |
| Loopback assumptions | `HermesRuntimeClient` rejects non-loopback HTTP URLs by default. Gateway runtime endpoints still use loopback caller controls. | Low | Keep non-loopback use explicit for Tailscale or test environments. |
| Runtime caller controls | Runtime endpoints are unauthenticated only inside the local caller boundary. Rejected non-loopback runtime calls are audited by existing local-binding controls. | Medium | Add optional runtime shared-secret or mTLS when multiple local processes become trusted callers. |
| Capability grants | TUA, browser assistance, and voice runtime paths still require capability checks through the centralized helper. | Low | Build grant review/revocation UX before beta. |
| Approval escalation | Runtime client can request approvals but cannot approve them. Approval decisions still require signed mobile routes. | Low | Keep all future helpers on runtime result endpoints, not mobile decision endpoints. |
| Operator session exposure | Signed mobile clients can list operator sessions. Runtime can poll subtype result endpoints it created. | Medium | Add ownership filters before multi-user support. |
| Mission visibility | Signed mobile clients can list all local gateway missions. | Medium | Add user/team scoping before enterprise or shared-device deployments. |
| Audit coverage | Demo path creates audit entries for notification, approval, TUA, browser assistance, voice, and mobile decisions. | Low | Add mission-specific audit events if mission management becomes active control, not just projection. |

## Risks

- A compromised local Hermes process can create noisy approval, assistance, notification, and voice requests.
- A trusted local caller allowlist that includes broad LAN addresses would weaken the loopback-first model.
- Polling result endpoints can create load if a runtime uses very short intervals across many missions.
- Mission IDs supplied by runtime are trusted as identifiers; collisions update existing mission projections.

## Recommendations

1. Keep runtime endpoints loopback-only by default.
2. Treat Tailscale access as mobile-to-gateway access, not runtime-to-gateway LAN exposure.
3. Add runtime caller identity stronger than source address before supporting multiple local runtime processes.
4. Add per-runtime rate limits for notification and approval creation.
5. Add mission ownership and operator visibility scopes before multi-user support.
