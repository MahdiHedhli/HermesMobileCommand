# ACT Clearance Proof Format

`act.clearance.v1` clearances include a tower proof so aircraft can verify a
returned clearance before executing.

The proof is an Ed25519 signature over this exact UTF-8 canonical string:

```text
ACT-CLEARANCE-PROOF-V1
<approval_id>
<params_fingerprint>
<short_code>
<risk_family>
<expires_at>
<tower_id>
<contract_version>
<extensions_digest>
```

Bound fields:

- `approval_id`
- `params_fingerprint`
- `short_code`
- `risk_family`
- `expires_at`
- `tower_id`
- `contract_version`
- `extensions_digest`

Verification recipe:

1. Recompute `params_fingerprint` from the redacted request payload and the
   `extensions` envelope.
2. Recompute `extensions_digest` from canonical JSON for the extensions object.
3. Verify `risk_family`, `short_code`, and `params_fingerprint` match the
   aircraft's pending request.
4. Build the canonical proof string exactly as above.
5. Verify the Ed25519 signature using the tower public key for `proof.key_id`.
6. Fail closed on mismatch, missing fields, expired clearance, unknown tower key,
   or invalid signature.

`tower_unavailable`, `verification_failed`, and `invalid` are aircraft-side
client outcomes. They are not ACT-issued clearance states.
