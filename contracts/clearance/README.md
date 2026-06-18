# ACT Clearance Contract

Canonical contract version: `act.clearance.v2`

Files:

- [clearance.schema.json](clearance.schema.json) is the language-neutral schema.
- [proof-format.md](proof-format.md) defines the tower proof signature format.
- [test-vector.json](test-vector.json) is the committed verification vector.

Compatibility:

- `act.clearance.v2` promotes `capability` to a core field. ACT resolves
  `risk_family` from the tower-owned capability registry when `capability` is
  present.
- `act.clearance.v1` AgenticKVM-style requests with
  `extensions.agentickvm.capability` are still accepted. ACT copies that value
  into core `capability` and emits a deprecation audit event on the clearance
  request.
- The committed test vector remains a v1 proof vector to prove the verifier
  remains version-aware and backward compatible.

ACT-issued clearance states:

| ACT state | Meaning |
| --- | --- |
| `pending` | Clearance is required and no final operator decision exists. |
| `approved` | Operator granted clearance through an eligible channel. |
| `denied` | Operator denied clearance. |
| `expired` | Clearance expired before approval. |
| `cancelled` | Runtime or tower cancelled the request. |

AgenticKVM mirror mapping:

| AgenticKVM state | ACT state |
| --- | --- |
| `clearance_required` | `pending` |
| `cleared` | `approved` |
| `denied` | `denied` |
| `expired` | `expired` |

`cancelled` currently has no AgenticKVM mirror equivalent.

Aircraft-side client conditions:

- `tower_unavailable`
- `verification_failed`
- `invalid`

These are not ACT-issued tower states. They describe the aircraft client's local
view of connectivity, proof verification, or request validation.
