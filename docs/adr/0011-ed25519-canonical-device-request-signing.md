# ADR-0011: Ed25519 Canonical Device Request Signing

## Status

Accepted

## Date

2026-06-04

## Context

Paired devices need to authorize sensitive mobile control-plane requests without relying on bearer tokens alone. Approval decisions, device management, notification history, audit history, and intervention placeholders must reject tampered, replayed, stale, unknown-device, or revoked-device requests.

## Decision

Use Ed25519 signatures over a canonical request string for paired-device control requests.

Canonical string:

```text
HMCP-SIGN-V1
METHOD
/v1/path?query
unix_timestamp_seconds
nonce
sha256(raw_request_body)
```

Required headers:

- `X-HMCP-Device-Id`
- `X-HMCP-Timestamp`
- `X-HMCP-Nonce`
- `X-HMCP-Signature`

The gateway verifies the device public key stored during pairing, rejects timestamps outside a 300 second window, and stores `(device_id, nonce)` to prevent replay.

## Consequences

Positive:

- Sensitive requests bind method, path, query, timestamp, nonce, and exact body bytes.
- Bearer-token theft alone cannot approve or deny actions.
- Revoked devices fail closed.
- Replay attempts are rejected and audited.

Negative:

- Mobile clients must preserve exact request bytes while signing.
- Clock skew beyond 300 seconds fails requests.
- Future key rotation needs clear mobile UX and recovery handling.

## Follow-Up

- Add key rotation tests once rotation endpoints are implemented.
- Define passkey or biometric unlock policy before production approval UX.
- Consider key identifiers if multi-key devices become common.
