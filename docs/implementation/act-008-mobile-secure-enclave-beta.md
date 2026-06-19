# ACT-MOBILE-BETA — Mobile Secure-Enclave Beta (mobile_signed)

**Spec**: [specs/003-mobile-beta/spec.md](../../specs/003-mobile-beta/spec.md)
**Branch**: `003-mobile-beta` (based on `001-hermes-mobile-command` @ `10f8fc7`, ACT-007 tip)
**Date**: 2026-06-19

Makes `mobile_signed` real on iOS: a native Secure-Enclave-backed, non-exportable
ECDSA P-256 signing key with biometric/user-presence per signature, wired through the
Flutter app, pairing with ACT via a real possession proof, signing decisions over the
canonical string the gateway verifies, and verifying ACT's published clearance proof
fail-closed. The app **conforms** to the ACT-001..007 authority core; it does not
reinvent the contract.

## What was built (per component / commit)

1. **Gateway — additive ECDSA P-256 device signing** (`4493688`). A genuine Secure
   Enclave key can only be P-256 (Ed25519 cannot run in the enclave). The gateway now
   verifies P-256 device signatures for `mobile_signed` devices: per-device
   `device_key_algorithm` recorded at enrolment (column + migration, default
   `ed25519`); P-256 = X9.63 public point + DER ECDSA-SHA256 signature; a P-256
   enrolment **requires** an enclave-signed possession proof over the pairing
   challenge. The canonical signing string, channel policy, replay/nonce/window, and
   proof format are **unchanged**. Ed25519 path preserved. `signing.py`,
   `store.py`, `storage/identity.py`, `schemas.py`, `routers/identity.py`,
   `tests/test_p256_signing.py`.
2. **Dart fail-closed proof verifier** (`e4c9939`). `clearance/canonical_json.dart`
   (byte-exact `json.dumps(sort_keys, separators, ensure_ascii)`) and
   `clearance/clearance_proof_verifier.dart` (rebuild the 9-line canonical proof
   string, Ed25519-verify against the pinned tower key, recompute
   short_code/extensions_digest/params_fingerprint, expiry + out-of-band capability),
   fail-closed.
3. **iOS runner + native Secure-Enclave signing** (`2d58f94`). Scaffolded `mobile/ios/`
   (was web-only). `Runner/SecureEnclaveSigner.swift` generates a non-exportable
   `SecureEnclave.P256.Signing.PrivateKey` with a `SecAccessControl` user-presence
   gate and signs the HMCP request / per-decision payload / possession proof behind
   Face ID; honest software-P256 fallback on the Simulator (never reported as
   hardware-backed). Dart bridge + signer, tower-key pinning (TOFU from
   `node_fingerprint`), pairing possession proof, real per-decision signature, honest
   native-sourced protection, and `app_runtime` enrolment without ever storing a
   private key. The pre-existing inbox already provides the multi-clearance queue.

## Verification matrix (honest)

States: **CC** code-complete · **SIM** simulator-verified · **DEV** real-device-verified
(physical Secure Enclave) · **GW** live-gateway-verified · **TF** TestFlight-distributed.
`—` = not yet done; `n/a` = not applicable; ⚠️ = partial, see note.

| Capability | CC | SIM | DEV | GW | TF |
|---|---|---|---|---|---|
| iOS Runner builds (`xcodebuild` BUILD SUCCEEDED) + launches/renders | ✓ | ✓ | — | n/a | — |
| **Secure-Enclave P-256 key, non-exportable** (the row that matters most) | ✓ | ⚠️¹ | — | — | — |
| Biometric (Face ID) gate per signature | ✓ | ⚠️² | — | — | — |
| Gateway accepts P-256 device signatures (additive) | ✓ | ✓³ | n/a | — | n/a |
| Pairing: enclave pubkey + enclave-signed possession proof | ✓ | — | — | — | — |
| Tower public key pinned at pairing (TOFU) | ✓ | — | — | — | — |
| HMCP transport signature (P-256) accepted by gateway | ✓ | — | — | — | — |
| Real per-decision signature over canonical signed_payload | ✓ | — | — | — | — |
| ACT-CLEARANCE-PROOF-V1 verify PASS on valid proof | ✓ | ✓⁴ | — | — | — |
| Proof verify FAILS CLOSED (mutation/expiry/unknown-key/bad-sig/bad-algo) | ✓ | ✓⁴ | — | — | — |
| Version-aware: committed v1 vector + v2 proof | ✓ | ⚠️⁵ | — | — | — |
| Honest ClearanceKeyProtection reporting | ✓ | ⚠️⁶ | — | n/a | — |
| Multi-clearance queue (existing inbox) | ✓ | ✓ | — | — | — |
| Single-shot decision (double-submit → 409) | ✓ | ✓³ | — | — | — |
| End-to-end low-risk clearance loop | ✓ | — | — | — | — |

Notes:
1. The Simulator has **no Secure Enclave**; the SIM run uses the honest software-P256
   fallback, reported as `hardwareBacked: false`. A real enclave key is **only**
   "DEV" once it signs on the physical iPhone 15 Pro Max — **not yet done**.
2. Biometric enforcement is via the enclave key's `SecAccessControl`; not yet
   exercised on device. The Simulator can simulate Face ID for UX.
3. Gateway pytest: **148 passing** (141 baseline + 7 new P-256 tests). Direct,
   not via the iOS app yet.
4. Dart unit tests (21) against the committed `contracts/clearance/test-vector.json`
   (v1) and a self-consistent generated v2 clearance, run on the Dart VM / Flutter
   test (counts as SIM-equivalent). The committed-vector signature passing proves the
   canonical proof-string reconstruction matches the gateway byte-for-byte.
5. v1 vector verified; v2 verified against a **synthetic** self-signed clearance. A
   **real** live v2 proof from a running gateway is **not yet** verified (GW).
6. The native→UI protection mapping is implemented; not yet visually confirmed on
   device/sim.

### Android (added 2026-06-19, D6 — code-complete parity)

| Capability (Android) | CC | emulator | DEV (StrongBox/TEE) | GW | store |
|---|:--:|:--:|:--:|:--:|:--:|
| Android runner builds (`flutter build apk --debug` ✅) + launches/renders | ✓ | ✓ | — | n/a | — |
| Native Keystore channel registered + Settings stable | ✓ | ✓ | — | — | — |
| Keystore P-256 key, non-exportable, user-auth-required | ✓ | ⚠️⁷ | — | — | — |
| BiometricPrompt-gated signing (BIOMETRIC_STRONG \| credential) | ✓ | ⚠️⁷ | — | — | — |
| Same `act/secure_enclave` channel → gateway P-256 verifies | ✓ | — | — | — | — |

7. Tracks iOS: an **emulator** has only software keymaster (no StrongBox/TEE), so it
   can prove the flow but would be honestly reported `hardwareBacked: false`. A real
   StrongBox/TEE signature needs a **physical Android device** (none present). The APK
   builds and the app launches + renders on the `act_test` (pixel_7, API 35) emulator;
   key generation round-trips through the channel only after pairing against a reachable
   gateway (GW). Real-device verification is the remaining step.

**Backend no-regression**: `uv run --project gateway pytest` → 148 passed (was 141).
`flutter analyze` clean. `flutter test` → 40 passed. `specify check` green
(it validates installed tooling only, not spec content). ACT-001..007 behavior
unchanged (canonical signing string, proof format, channel policy, capability
registry untouched; P-256 support is purely additive).

## Beta-testable NOW

- The gateway P-256 path, the fail-closed proof verifier, and the canonical-JSON
  encoder are verified by automated tests (148 gateway + 40 Dart).
- The iOS app builds and launches/renders on the Simulator.

## What the operator must do (cannot be done autonomously)

1. **Apple signing identity** (D3, stage 1 — free/personal on-device first): add your
   Apple ID in **Xcode → Settings → Accounts** (enables a free "Personal Team"), then
   set the Runner target's Team and a unique bundle id (current placeholder:
   `app.act.agenticControlTower`). This requires your interactive Apple-ID 2FA — I
   cannot do it. Once set, `flutter run -d <device>` deploys to the paired
   **Meta42iPhone (iPhone 15 Pro Max, A17 Pro)** and the Secure-Enclave row becomes
   verifiable on real hardware.
2. **Test gateway endpoint** (D4): a tailnet/LAN address the phone can reach (loopback
   `127.0.0.1:8787` is unreachable from the device). Run the gateway on a tailnet host
   and set the URL in the app's Settings. Then create a pairing session pinned to
   `mobile_signed` and complete the loop.
3. **TestFlight** (D3, stage 2): a paid Apple Developer account + App Store Connect
   app record + 2FA. I prepare the archive up to the interactive upload step.

## Remaining gaps / honest limits

- **The hardware-backed key has not signed on a real Secure Enclave yet** — it is
  code-complete and the gateway accepts P-256, but real-device verification awaits the
  Apple signing identity above. Until then, do not report it as device-verified.
- The full pair → clearance → Face-ID-approve → proof-verify → decision loop has not
  run against a live gateway (GW column empty).
- `flutter build ios --simulator` reports a generic "Exited with status code 255" on
  Xcode 26.5 while parsing the xcresult, even though `xcodebuild` itself returns
  **BUILD SUCCEEDED**. This is a Flutter↔new-Xcode tooling quirk, not a compile error;
  building/running via `xcodebuild`/`flutter run` works. Worth pinning the cause
  before relying on `flutter build` in CI.
- The proof-verification VERDICT is wired into `app_runtime.verifyClearanceProof()` but
  not yet surfaced as a VERIFIED/REJECTED badge in the reduced `ApprovalAlpha` UI
  (requires threading the raw proof through the presentation layer).
- Real-v2-proof canonical-JSON byte-exactness can only be fully confirmed against a
  live gateway proof (the committed vector is v1 with `params_fingerprint = ffff…`).

## Out of scope (do NOT start — other threads)

- The two ACT-003.2 residuals: AgenticKVM mirror migration to `act.clearance.v2`, and
  hardware **attestation** of clearance-key origin. (Running an enclave key on a real
  device is permitted validation; cryptographically attesting its enclave provenance
  to the tower is the residual.)
- The AgenticKVM mirror.

## Next steps

1. Operator adds the Apple signing identity; deploy to Meta42iPhone via `flutter run`.
2. Stand up the gateway on a tailnet host; pair (operator pins `mobile_signed`),
   exercise a low-risk clearance end-to-end on hardware; fill the DEV + GW columns.
3. Surface the proof VERIFIED/REJECTED badge in the approval UI.
4. Resolve the `flutter build ios --simulator` xcresult 255 quirk.
5. Stage 2: TestFlight once the paid account is available.
