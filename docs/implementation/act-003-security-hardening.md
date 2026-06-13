# ACT-003 Security Hardening

ACT-003 hardens the tower's clearance authority in three areas: mobile key
posture, notification composition, and channel policy.

## Hardware-Backed Mobile Keys

The Flutter alpha now exposes clearance-key protection metadata in settings:

- key backend
- hardware-backed status
- user-presence status
- production readiness
- warning text

Current repository state:

- Web/dev uses `development_exportable_ed25519`.
- Native Flutter secure storage reports `flutter_secure_storage_exportable_ed25519`.
- The repo does not currently include `ios/` or `android/` platform folders.
- Secure Enclave and Android Keystore signing are not device-verified in this
  sprint.

This means the mobile code is honest about fallback posture, but production
hardware-backed, non-exportable, user-presence-gated signing still requires a
native implementation and real-device validation.

## Notification Composition

Backends may still submit legacy `title` and `body` fields for compatibility,
but ACT does not echo them into visible notification text. ACT composes:

- push title
- push body
- notification preview
- mobile notification summary

from allowlisted template fields such as subject display name, risk family,
operation label, urgency, category, and pending count.

Secret-like, token-like, oversized, or high-entropy raw text is treated as a
backstop signal. ACT sanitizes to safe fallback template text and audits the
unsafe input detection in `notification_queued`.

## Clearance Channel Policy

ACT owns channel eligibility. Backends cannot define channel rules or assert
their own deployment trust context.

Supported channels:

- `mobile_signed`
- `local_terminal`

Risk-tier defaults:

- `observe`, `read_only`, `routine`: mobile or local terminal when local is
  enabled.
- `external_effect`, `destructive`, `credential_or_secret`, `safety_critical`,
  `irreversible`: mobile mandatory.

Deployment trust contexts:

- `trusted_host`
- `untrusted_host`
- `adversarial_host`

Local-terminal is disabled for untrusted and adversarial hosts even when both
channels are configured. Decisions through ineligible channels are rejected,
audited, and leave the clearance pending.

## Open Item

The backend-provided risk family is currently trusted for routing. The next
security iteration should add a tower-owned capability registry that validates
or pins risk family per backend capability.
