# ACT-007 Capability Registry

ACT now owns risk tiering for known capabilities.

## What Changed

- Added a tower-owned capability registry keyed by derived aircraft principal
  and capability: `(node_id:agent_id, capability)`.
- Aircraft can propose capability risk pins for its own derived principal.
  Proposals are stored as `pending` and have no authority until approved.
- Operators approve or reject pending entries through signed device requests
  with the `manage_capabilities` permission.
- Approved pins are authoritative. A clearance request whose `risk_family`
  differs from the approved pin is rejected and escalated.
- Unknown capabilities resolve to `external_effect` by default, which makes
  them mobile-mandatory through the existing channel policy. Agents can opt into
  `require_classified_capabilities`, which hard-rejects unknown capabilities.
- `capability` is promoted to the core clearance contract in
  `act.clearance.v2`. v1 AgenticKVM-style extension capability remains accepted
  with a deprecation audit.

## Enforcement

Capability risk resolution happens before approval persistence, proof creation,
and channel eligibility. The resolved risk family is what ACT stores, tiers, and
binds into the clearance proof. Channel policy is not reimplemented in this
layer.

Mismatch handling is strict in both directions:

- Aircraft claims lower risk than the approved pin: reject and emit a security
  severity `capability_risk_mismatch`.
- Aircraft claims higher risk than the approved pin: reject and emit a drift
  severity `capability_risk_mismatch`.

Unknown capability handling:

- Default: resolve to `external_effect`, emit `capability_unclassified`, and
  allow the clearance to proceed at the fail-closed tier.
- `require_classified_capabilities=true`: reject with `capability_unclassified`.

## Safe Alerts

Capability registry alerts use the ACT notification compositor. Audit metadata
uses safe labels and categorical reasons; raw aircraft text is not echoed into
operator-visible notification text.

## Honest Limit

The registry pins risk for a known capability, but ACT still trusts the aircraft
to identify which capability it is invoking. This reduces the trust problem from
"trust the aircraft's risk label" to "trust the aircraft's capability claim."
Future work should bind known capabilities to typed payload schemas and adapter
capability manifests.
