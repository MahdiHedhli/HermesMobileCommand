# ADR-0003: Device Key Pairing And Signed Approvals

## Status

Accepted

## Date

2026-06-04

## Context

Tailscale identity grants network reachability but should not by itself authorize mobile control. Approvals and emergency interventions are safety-critical and must resist replay, token theft, and stale decisions.

## Decision

Each mobile app installation generates a device keypair during pairing. The gateway registers the device public key. Session tokens authorize ordinary API access, while approvals and emergency interventions require signed request bodies from the device key.

## Consequences

Positive:

- A newly installed app becomes trusted only through local pairing.
- Approval decisions are attributable to a device.
- Replay and token theft risks are reduced.
- Lost devices can be revoked gateway-side.

Negative:

- Key lifecycle, recovery, and revocation must be implemented carefully.
- Device secure storage behavior differs across iOS and Android.
- Multi-device conflict handling is required.

## Follow-Up

- Define canonical signing payloads.
- Add device revocation and key rotation flows before approvals ship.
