# Implementation Plan: Mobile Secure-Enclave Beta (mobile_signed)

**Branch**: `003-mobile-beta` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-mobile-beta/spec.md`

## Summary

Close the `mobile_signed` gap on iOS: scaffold the iOS runner, add a native Secure-Enclave signing module behind a Flutter platform channel (non-exportable key, user-presence per signature), make pairing send a real possession proof on the operator-pinned channel, implement a fail-closed `ACT-CLEARANCE-PROOF-V1` verifier with a byte-exact canonical-JSON encoder, replace the placeholder per-decision signature with a real enclave signature, report protection state truthfully, and deliver a beta build that runs on a physical Secure-Enclave device. The app conforms to the published ACT contract; the backend authority core (ACT-001..007) is not changed except — pending decision **D1** — an additive gateway path to verify ECDSA P-256 device signatures for `mobile_signed` devices (required for a genuine Secure Enclave key, since the Enclave cannot hold Ed25519).

## Technical Context

**Language/Version**: Gateway = Python 3.12+/FastAPI (`uv`), verified baseline **141 pytest passing**. Mobile = Flutter/Dart (currently web-only, software Ed25519). Native iOS module = Swift (Security framework / CryptoKit `SecureEnclave.P256`).

**Primary Dependencies**: Published contract (`contracts/clearance/`), `gateway/src/hermes_gateway/{signing,clearance_contract,clearance_policy,routers/identity}.py`, Flutter (`local_auth` or native LAContext; platform channel), Xcode 26.5.

**Storage**: iOS Keychain holds only the public key + an opaque enclave key reference; no private key bytes. Tower public key pinned per `tower_id` (TOFU). No private-key persistence.

**Testing**: `flutter analyze` + `flutter test` (incl. proof-verifier conformance against `contracts/clearance/test-vector.json` + a live v2 proof, and biometric-gated signing behind a native mock); gateway `uv run --project gateway pytest` MUST stay ≥141; `uvx --from git+https://github.com/github/spec-kit.git specify check` green; real-device + live-gateway manual verification on the physical iPhone.

**Target Platform**: iOS (physical Secure-Enclave device: iPhone 15 Pro Max / iPhone16,2, A17 Pro). Android deferred (Decisions Pending D5/scope).

**Project Type**: Mobile app + local gateway control-plane service.

**Performance Goals**: Biometric prompt + sign + submit should feel immediate; proof verification is local and sub-100ms. Exact budgets are not gating for beta.

**Constraints**: Self-hosted first, Tailscale first; fail-closed approvals; non-exportable hardware key; honest capability-state reporting; no regression of ACT-001..007; do not start the two ACT-003.2 residuals or touch the AgenticKVM mirror.

## Constitution Check

The constitution file is still template placeholders; accepted ADR/contract constraints apply as gates:

- Channel policy: `mobile_signed` is the only authority; `local_terminal` never authority; mobile-mandatory risk families; operator-pinned channel at pairing (ACT-003.1.1).
- Ed25519 canonical device-request signing + 300s window + `(device_id, nonce)` replay (ADR-0011) — canonical *string* unchanged; algorithm support additive only (D1).
- Approval engine fails closed (ADR-0006); push is a hint, not state (ADR-0005).
- Tower-authoritative fields (`params_fingerprint`, `short_code`, `extensions_digest`, `risk_family`, capability risk pins) — app verifies, never overrides.
- Honesty discipline: code-complete vs simulator vs real-device vs live-gateway vs TestFlight; no overclaiming.

## Project Structure

### Documentation

```text
specs/003-mobile-beta/
├── spec.md
├── plan.md
├── tasks.md            (added before /speckit-tasks; pending decisions)
└── checklists/
    └── requirements.md

docs/
├── implementation/act-008-mobile-secure-enclave-beta.md   (planned: build/verification report)
└── security/                                              (proof-verify + enclave notes as needed)
```

### Source Code

```text
mobile/
├── ios/                         (NEW — Runner Xcode project, Info.plist w/ NSFaceIDUsageDescription, entitlements, Podfile)
│   └── Runner/SecureEnclaveSigner.swift   (NEW — native SE key + biometric sign over a platform channel)
├── lib/src/security/            (replace exportable Ed25519 path; native-backed signer; honest protection)
├── lib/src/clearance/           (NEW — ACT-CLEARANCE-PROOF-V1 verifier + byte-exact canonical JSON)
├── lib/src/repositories/        (real per-decision signature; pairing possession proof; tower-key pinning)
└── test/                        (rewrite insecure-contract assertions; add proof-verifier + signing tests)

gateway/                         (D1, additive only: accept ECDSA P-256 device signatures for mobile_signed;
                                  per-device algorithm at enrolment; Ed25519 preserved; +tests)
```

**Structure Decision**: iOS is greenfield (only `mobile/web/` exists today). Native signing lives behind a platform channel so Dart stays the app surface and the Enclave stays the key authority. The gateway change (if D1=A) is strictly additive and must keep the 141-test baseline green.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Native Secure-Enclave P-256 signer (D1=A) | A real non-exportable hardware key on Apple HW can only be P-256; this is the mission's core proof point | Keeping software Ed25519 cannot be honestly reported as Secure-Enclave-backed; a Keychain Ed25519 key (D1=B) is weaker on non-exportability and still not Enclave-resident |
| Additive gateway P-256 verification (D1=A) | The enrolled device key must verify server-side under the canonical signing string | Changing the canonical string would regress ACT-001..007; not adding P-256 would make a real Enclave key unusable |
| Byte-exact Dart canonical-JSON encoder | `params_fingerprint`/`extensions_digest` must match `sort_keys=True, separators=(",",":")` exactly | Dart `jsonEncode` does not sort keys; any drift fails valid proofs closed (false negatives that look like security) |
| Honest simulator/web degrade | Simulator has no Secure Enclave | Reporting a simulator pass as hardware-backed violates the honesty discipline |
