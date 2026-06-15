# Clearance Channel Policy

ACT owns clearance channel policy for every backend adapter. Backends request
clearance; they do not choose the channel rules, deployment trust context, or
which channel is sufficient for a risk family.

## Channels

- `mobile_signed`: default and recommended. A paired operator phone signs the
  decision out-of-band from the backend host.
- `local_terminal`: opt-out local render surface. It must route through ACT and
  use server-verified Ed25519 signatures from a registered terminal principal.
  The terminal is not the authority.

When both channels are enabled, risk-tier rules still apply. Both never means
either channel may clear every action.

## Risk Families

Low-risk reversible families may use mobile or local-terminal when local is
enabled:

- `observe`
- `read_only`
- `routine`

Mobile-mandatory families:

- `external_effect`
- `destructive`
- `credential_or_secret`
- `safety_critical`
- `irreversible`

Unknown risk families fail closed as external-effect style risk.

## Tower-Owned Trust Context

Deployment trust context is configured by the operator at the tower per
registered aircraft/agent:

- `trusted_host`
- `untrusted_host`
- `adversarial_host`

Backends cannot supply or override this context. External clearance request
schemas reject `deployment_trust_context` and `channel_eligibility` with `422`.
Any remaining internal path that encounters those fields must ignore them and
audit the override attempt as defense-in-depth.

This prevents a compromised co-resident backend from declaring itself trusted
and re-enabling the local-terminal channel.

## Enforcement

Every clearance decision evaluates:

- channel derived from the authenticated principal's enrolled class
- risk family
- eligible channels
- tower-configured deployment trust context
- device or local-terminal identity

Channel eligibility is enforced only for authority-granting transitions. Deny,
expire, and cancel transitions are authority-reducing and may be submitted from
any authenticated channel, while still auditing the actual channel and risk
metadata. Rejected grant attempts create `clearance_channel_rejected` audit
events and do not change approval state.

Successful decisions store channel metadata in approval `decision_metadata` and
the `approval_decision` audit payload.

## Known Limitation

ACT-003 still accepts the backend-supplied risk-family label for routing. This
is explicit technical debt. A later capability registry should pin risk family
per known backend capability so a dishonest or compromised backend cannot label
a high-risk action as routine.

ACT-003.1 removes route/client assertion of the clearance channel, but does not
provide hardware attestation that an enrolled `mobile_signed` key was generated
inside Secure Enclave or Android Keystore. The enrolled channel class is still
an enrollment-time assertion until native device attestation is validated.
