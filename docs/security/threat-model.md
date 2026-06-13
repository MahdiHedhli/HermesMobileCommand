# Threat Model

## Scope

This threat model covers Agentic Control Tower across:

- Mobile apps
- ACT Gateway
- Runtime adapters
- Agentic backends
- Hermes adapter #1
- MCP tools where a backend exposes them
- Browser subsystem
- Voice subsystem
- Push notification framework
- Tailscale and trusted local connectivity
- Optional future relay service

It assumes self-hosted first, Tailscale first, no required public exposure, and device-key-based mobile trust.

ACT is backend-neutral. A backend is an aircraft requesting clearance; ACT is
the control tower. ACT does not execute backend actions. It receives translated
requests from adapters, applies policy, records audit events, and verifies
operator decisions from paired devices.

## Security Goals

- Prevent unauthorized access to ACT-controlled backends.
- Prevent unauthorized clearances or broadened clearance scopes.
- Prevent secrets from leaking through mobile notifications or event streams.
- Preserve auditability for consequential events.
- Fail closed for stale, malformed, replayed, or policy-denied approvals.
- Allow quick revocation of lost or compromised devices.
- Avoid requiring public exposure for self-hosted backends.

## Assets

| Asset | Sensitivity | Protection Goal |
| --- | --- | --- |
| Device private key | Critical | Never leaves secure device storage |
| Gateway device registry | Critical | Only trusted local admin/pairing can mutate |
| Clearance requests and decisions | Critical | Tamper-evident, scoped, replay-resistant |
| Backend work state and conversations | High | Accessible only to authorized devices |
| Consequential action payloads and outputs | High | Redacted before mobile display when needed |
| Secrets, credentials, tokens | Critical | Never appear in push title/body; redacted in streams |
| Audit log | High | Append-only, integrity protected, locally recoverable |
| Push tokens | Medium | Usable only for notification dispatch; revocable |
| Voice audio/transcripts | High | Tied to work context, redacted where applicable |
| Browser screenshots/work state | High | Only streamed to authorized devices |
| Tailscale identity | High | Not sufficient alone for app-level trust |

## Actors

| Actor | Description |
| --- | --- |
| Owner/operator | Trusted user managing one or more ACT-controlled backends |
| Registered mobile device | Device trusted by gateway pairing and public key registration |
| Operator device | Clearance authority for sensitive decisions |
| ACT Gateway | Self-hosted control tower enforcing policy and audit |
| Runtime adapter | Translation layer between backend-specific requests and ACT concepts |
| Agentic backend | Runtime or agent requesting notices, clearances, handoffs, and state updates |
| Hermes adapter | First concrete RuntimeAdapter implementation |
| MCP tool | Tool execution surface under backend and gateway policy |
| Push provider | APNs/FCM; trusted for transport but not confidentiality |
| Optional relay | Future connectivity broker; not required and not inherently trusted |
| Local attacker | Has access to LAN/tailnet or a host near the gateway |
| Remote attacker | No trusted network access but may phish, replay, or target exposed services |
| Malicious/rogue backend | Backend pretending to be legitimate or sending abusive requests |
| Untrusted agent sharing the gateway host | Future hardening actor: local agent process with host-level reachability to gateway files or sockets |
| Compromised phone holder | Has access to a registered mobile device |

## Trust Boundaries

| Boundary | Crossed By | Main Risks |
| --- | --- | --- |
| Mobile device to private network | API calls, WebSocket, voice media | Device theft, token theft, MITM, stale sessions |
| Private network to gateway | All mobile control traffic | Tailscale credential theft, rogue local client |
| Gateway to runtime adapter | Backend events, clearance requests, handoffs | Rogue backend, malformed events, policy bypass |
| Adapter to backend/tools/browser | Consequential execution outside ACT | Destructive actions, credential access, external side effects |
| Gateway to local PTY prototype | Mobile TUI streams | Shell escape, privilege misuse, sensitive output exposure |
| Gateway to push providers | Push requests | Secret leakage, notification spoofing/abuse |
| Optional relay boundary | Future proxied traffic | Relay compromise, metadata leakage, session hijacking |

## Attack Surfaces

- Pairing endpoint and short-lived pairing code
- Device registration and revocation endpoints
- REST API session tokens
- WebSocket event stream
- Clearance decision endpoint
- Emergency intervention endpoint
- Push token registration
- `mobile_notify` tool
- Backend and subject registration and health endpoints
- Browser state and takeover endpoints
- Development-only local PTY TUI endpoints and WebSocket stream
- Voice session creation and media transport
- Audit export endpoints
- Optional relay ingress

## Abuse Cases

| Abuse Case | Impact | Mitigations |
| --- | --- | --- |
| Attacker grants clearance for a destructive shell command | Data loss or compromise | Device-key signatures, clearance expiry, action binding, audit, high/critical scope limits |
| Agent floods phone with push notifications | Alert fatigue, denial of attention | Rate limits, dedupe, category quotas, policy rejection, audit |
| Rogue backend impersonates a trusted backend | Unauthorized data/control path | Explicit pairing, node fingerprint, device registry, user-visible backend identity |
| Secret appears in push body | Credential leakage through OS notification surfaces | Secret scanner, payload minimization, rejection audit |
| Stale approval is replayed | Unauthorized action after context changed | `approval_id`, `decision_id`, expiry, signed payload hash, idempotency store |
| Lost phone remains trusted | Unauthorized control | Device revocation, session invalidation, emergency revoke from gateway |
| Tailscale identity stolen | Network reachability to gateway | App-level device identity, session token binding, gateway authorization |
| Browser takeover abused | Session hijack or data exposure | Capability gating, active session confirmation, audit, read-only default |
| Local PTY prototype abused | Direct shell access to the gateway host | Disabled by default, signed session creation, access-token stream, command allowlist, working directory root, max sessions, idle timeout, metadata-only audit |
| Voice command misheard as approval | Unsafe action | Confirmation phrase, touch fallback, high/critical touch requirement |
| Optional relay observes sensitive payloads | Confidentiality loss | No relay required, future app-layer encryption, minimal relay storage |

## Failure Modes

| Failure Mode | Expected Behavior |
| --- | --- |
| Gateway cannot reach backend | Show backend degraded; disable actions needing that backend; keep audit accessible |
| Mobile app offline during clearance | Clearance expires or remains pending; backend must not proceed without valid clearance |
| Push provider unavailable | Durable approval remains in queue; dispatch failure audited |
| Event cursor expired | Mobile fetches current snapshots and resumes from latest cursor |
| Device key lost | Device must be re-paired; old device identity revoked |
| Audit store unavailable | Gateway refuses consequential actions if audit cannot be recorded |
| Policy engine unavailable | Gateway fails closed for consequential actions |
| TUI local PTY disabled or policy rejects command | Mobile falls back to mock/planned state; no shell starts |
| Voice provider unavailable | Voice capability degraded; text controls remain available |

## Scenario Evaluations

### Compromised Phone

Risk:

- Attacker may access sessions, approvals, and interventions until device is revoked.

Mitigations:

- Store private keys only in Keychain/Keystore.
- Require app unlock for approvals and emergency controls.
- Bind session tokens to device ID and rotate frequently.
- Allow gateway-side device revocation.
- Audit every decision with device ID.
- Optional future per-approval biometric/passkey confirmation.

Residual risk:

- If attacker has full device compromise and can use secure storage, gateway revocation is the primary containment.

### Lost Phone

Risk:

- Finder may attempt to use a still-registered device.

Mitigations:

- Local app unlock.
- Gateway revocation from Hermes host or another trusted device.
- Short-lived session tokens.
- Device status visible in settings.
- Emergency revoke all devices option.

Residual risk:

- Until revocation, a logged-in device may retain limited access depending on OS lock state.

### Stolen Tailscale Credentials

Risk:

- Attacker gains network reachability to the gateway.

Mitigations:

- Tailscale identity is not sufficient for API access.
- Gateway requires registered device session tokens.
- Pairing endpoints require short-lived local ceremony.
- Device public keys verify approval decisions.

Residual risk:

- Gateway metadata and exposed unauthenticated health endpoints must remain minimal.

### Rogue Or Malicious Backend

Risk:

- Malicious backend sends false clearance requests, abusive notifications, or misleading activity.

Mitigations:

- User explicitly pairs each node and sees node fingerprint.
- Node identity displayed in every action.
- Notification rate limits and secret filtering apply per node.
- Clearance scope cannot cross nodes.
- User can quarantine or remove node.

Residual risk:

- A paired rogue node can still send misleading summaries; operator trust in node remains necessary.

### Untrusted Agent Sharing The Gateway Host

Risk:

- A backend or agent process on the same host may be able to reach loopback
  services, observe local files, or attempt local storage tampering.

Current mitigations:

- Sensitive mobile decisions require paired-device signatures.
- Runtime-local APIs are loopback/allowlist controlled.
- Consequential actions should fail closed when policy or audit cannot run.
- Dangerous development features remain disabled by default.

Later hardening:

- Storage-forgery tests for audit, device registry, and clearance records.
- Stronger filesystem permissions and process isolation guidance.
- Separate runtime adapter credentials from mobile device credentials.
- Optional OS sandboxing or service user split for the gateway.

### MITM Attempts

Risk:

- Attacker intercepts or modifies traffic.

Mitigations:

- Tailscale encrypted transport by default.
- HTTPS for local/relay paths where available.
- Device-key signatures for clearances and interventions.
- Token binding to device ID.
- Gateway node fingerprint in pairing.

Residual risk:

- Local network HTTPS certificate handling must be designed carefully to avoid habituating users to warnings.

### Push Notification Abuse

Risk:

- Alert flooding, spoofed urgency, or secret leakage.

Mitigations:

- Gateway validates `mobile_notify`.
- Rate limits, dedupe, and urgency policy.
- Secret scanning rejects unsafe title/body.
- Push payloads contain only minimal IDs and safe text.
- Push events are auditable.

Residual risk:

- APNs/FCM delivery behavior is platform controlled.

### Replay Attacks

Risk:

- Old decisions reused for new actions.

Mitigations:

- Clearance and decision IDs.
- Signed decision includes clearance/action ID, scope, node, subject, work context, expiration, and payload hash.
- Idempotency store rejects duplicate decision IDs.
- Expired approvals fail closed.

Residual risk:

- Clock skew must be bounded and handled explicitly.

### Unauthorized Approvals

Risk:

- A user or attacker approves outside intended authority.

Mitigations:

- Device authorization policy.
- Clearance scope enforcement.
- Critical actions require explicit confirmation.
- Future multi-user role checks.
- Audit trail for every decision.

Residual risk:

- Single-user MVP treats registered devices as trusted operator devices.

### Token Theft

Risk:

- Session token used to call gateway APIs.

Mitigations:

- Short-lived access tokens.
- Refresh flow requires device key proof.
- Token scoped to node/device.
- Revocation invalidates refresh material.
- Consequential actions still require signed payloads.

Residual risk:

- Active token theft may allow read access until expiry.

### Session Hijacking

Risk:

- Attacker joins live event stream or voice session.

Mitigations:

- Authenticated WebSocket.
- Per-session authorization.
- Stream cursor scoped to node/device.
- Voice sessions require authenticated creation and short-lived media credentials.
- Browser takeover requires explicit capability and audit.

Residual risk:

- Full device compromise can still hijack active sessions until revocation.

## Threat Review Checklist

- Confirm no public exposure is required for self-hosted installs.
- Confirm pairing endpoints are disabled or short-lived by default.
- Confirm all consequential actions require policy evaluation.
- Confirm push payloads are secret-free.
- Confirm audit logging is append-only and cannot be silently disabled.
- Confirm device revocation invalidates sessions and push tokens.
- Confirm approval signatures bind exact action and scope.
- Confirm event streams enforce per-device authorization.
- Confirm voice approval cannot bypass touch/confirmation requirements.
