# ACT-003.2 Canonical Clearance Contract

Status: implemented

ACT now publishes `act.clearance.v1` as the canonical, versioned clearance
contract for aircraft mirrors.

Canonical artifacts:

- [Clearance contract](../../contracts/clearance/README.md)
- [JSON Schema](../../contracts/clearance/clearance.schema.json)
- [Proof format](../../contracts/clearance/proof-format.md)
- [Verification test vector](../../contracts/clearance/test-vector.json)

## What Is Real

- Clearance objects expose `contract_version`, `short_code`, `tower_id`,
  `proof`, `audit_correlation_id`, `operator_message`, `risk_family`,
  `expires_at`, `params_fingerprint`, and `extensions`.
- Runtime result and Hermes status polling return the same canonical fields as
  the rich approval object.
- ACT computes `params_fingerprint` server-side from canonical redacted payload
  plus the extensions envelope.
- ACT derives `aircraft` and `requested_by` from the authenticated local caller
  path and audits self-declared request values as ignored.
- `operator_message` is composed through ACT's notification allowlist path. Raw
  aircraft text is not echoed to the operator response or audit payload.
- The clearance proof binds `approval_id`, `params_fingerprint`, `short_code`,
  `risk_family`, `expires_at`, `tower_id`, `contract_version`, and
  `extensions_digest`.
- The `agentickvm` extension namespace round-trips the mirror fields `target`,
  `provider`, `capability`, `risk_summary`, and `policy_context`.

## What Did Not Change

- Channel-policy semantics are unchanged.
- Handoff clearance binding from ACT-005 is unchanged.
- Device request signing, nonce handling, and one-time consumption are unchanged.
- Hermes compatibility routes remain in place.
- ACT-issued clearance states remain `pending`, `approved`, `denied`,
  `expired`, and `cancelled`.

## Aircraft Verification

Aircraft should verify fail-closed:

1. Recompute `params_fingerprint` from its request's redacted payload and
   extensions.
2. Verify the returned `risk_family`, `short_code`, and `params_fingerprint`
   match the pending request.
3. Recompute the extensions digest.
4. Verify the Ed25519 proof using the tower public key for `proof.key_id`.
5. Treat `tower_unavailable`, `verification_failed`, and `invalid` as
   aircraft-side client states, not ACT-issued tower states.

## Remaining Work

- AgenticKVM should mirror this published contract instead of its temporary
  local reconstruction.
- Capability-registry validation is still needed so ACT can validate
  aircraft-supplied `risk_family` instead of only routing on it.
- Hardware attestation for clearance-key origin remains a separate native
  device validation item.
