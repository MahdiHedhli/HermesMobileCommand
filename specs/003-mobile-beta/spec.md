# Feature Specification: Mobile Secure-Enclave Beta (mobile_signed)

**Feature Branch**: `003-mobile-beta`
**Created**: 2026-06-19
**Status**: Approved — in implementation (operator decisions D1–D5 resolved 2026-06-19)
**Input**: Make `mobile_signed` real and ship a beta-testable iOS app. Deliver the operator's phone as a native Secure-Enclave-backed, non-exportable signing key with biometric/user-presence per clearance, wired through the Flutter app that pairs with ACT, receives clearance requests, approves them with a real on-device signature, and verifies ACT's published clearance proof fail-closed. Spec-first; honest reporting of what ran on hardware vs. what is only code-complete. Conform to the ACT-001..007 authority core; do not regress it.

## Summary

ACT's backend authority core (ACT-001..007) is complete: the v2 clearance contract, the published `ACT-CLEARANCE-PROOF-V1` proof format, the canonical signing string, the channel policy (`mobile_signed` is the only authority; `local_terminal` is never authority), the operator-pinned pairing channel (ACT-003.1.1), and the capability registry (ACT-007). The gap to a usable product is the operator's phone. Today the Flutter app (`mobile/`) is **web-only** (no `ios/`/`android/` runner), signs with an **exportable software Ed25519 key** generated in Dart, requires **no biometric**, sends a **hardcoded placeholder** as the per-decision signature, and has **no proof verifier**. This feature closes that gap on iOS: a real Secure-Enclave key, biometric per signature, an honest pairing possession-proof, a fail-closed proof verifier, and a beta build that runs on a physical Secure-Enclave device.

This spec is **conformance-driven**: the app mirrors the published contract and signs/verifies the exact byte strings ACT expects. It does not reinvent the contract.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pair the phone as a hardware-backed signer (Priority: P1)

As the operator, I pair my iPhone with my ACT gateway so the phone becomes a registered `mobile_signed` device whose signing key lives in the Secure Enclave and can never be exported.

**Why this priority**: Without a real hardware-backed enrolled key there is no authentic `mobile_signed` channel; every later step depends on it.

**Independent Test**: On a physical Secure-Enclave device, complete pairing against a live gateway and confirm the gateway registers the device's public key under the operator-pinned `mobile_signed` channel, and that the private key cannot be read back from the app.

**Acceptance Scenarios**:

1. **Given** the operator initiates pairing on the gateway with `clearance_channel` pinned to `mobile_signed`, **When** the app completes pairing, **Then** it generates a non-exportable Secure-Enclave key, sends the corresponding public key plus a key-signed possession proof, and the gateway enrols the device on the pinned channel.
2. **Given** the device attempts to self-declare a different `clearance_channel` than the operator pinned, **When** it completes pairing, **Then** the gateway rejects it (400, `device_clearance_channel_conflict`) and the app surfaces the rejection.
3. **Given** pairing succeeds, **When** the app stores trust material, **Then** it persists only the public key and an opaque Secure-Enclave key reference (never private key bytes), and it pins the tower public key for proof verification (trust-on-first-use, per `tower_id`).

### User Story 2 - Biometric-approve a clearance with a real on-device signature (Priority: P1)

As the operator, when an agent requests a clearance I receive it on my phone, see a safe composed message, and approve or deny it. Approval requires Face ID and produces a real Secure-Enclave signature that the gateway accepts.

**Why this priority**: This is the mission's core proof point — a real human-present, hardware-signed decision flowing through `mobile_signed`.

**Independent Test**: Trigger a low-risk clearance from a live gateway, approve it on the device behind a Face ID prompt, and confirm the gateway accepts the signed request and resolves the clearance exactly once.

**Acceptance Scenarios**:

1. **Given** a pending clearance arrives over the realtime stream, **When** the operator opens it, **Then** the app renders the ACT-composed `operator_message`/notification text and never raw aircraft-supplied text.
2. **Given** the operator taps Approve (or Deny), **When** the decision is submitted, **Then** the device requires Face ID / user presence and the Secure-Enclave key signs the canonical request; the gateway verifies the signature against the enrolled public key and resolves the clearance.
3. **Given** the operator submits a second decision for the same clearance, **When** it reaches the gateway, **Then** it is rejected (409, one-time consumption) and the app reflects the already-resolved state.
4. **Given** the clearance has expired, is denied, or is cancelled, **When** the operator views or acts on it, **Then** the app shows the terminal state and prevents a contradictory action.

### User Story 3 - Verify ACT's clearance proof fail-closed (Priority: P1)

As the operator, before I trust that ACT actually granted a clearance, my phone independently verifies ACT's published cryptographic proof and refuses to treat an unverifiable clearance as granted.

**Why this priority**: Fail-closed proof verification is the project's core safety value; a phone that displays "approved" without verifying the proof is unsafe.

**Independent Test**: Feed the app the committed `contracts/clearance/test-vector.json` proof and a live gateway proof; confirm valid proofs verify and any mutated/expired/unknown-key/bad-signature proof is rejected and surfaced as not-verified.

**Acceptance Scenarios**:

1. **Given** a clearance with a valid `ACT-CLEARANCE-PROOF-V1` proof, **When** the app verifies it, **Then** it rebuilds the canonical proof string, recomputes `params_fingerprint` and `extensions_digest` with a byte-exact canonical-JSON encoder, verifies the Ed25519 signature against the pinned tower key, confirms `capability` matches out-of-band, and shows VERIFIED.
2. **Given** any bound field is mutated, the proof is expired, the `tower_id`/key is unknown, or the signature is invalid, **When** the app verifies it, **Then** verification FAILS CLOSED and the app refuses to present the clearance as granted.
3. **Given** the committed v1 test vector and a live v2 proof, **When** the app verifies each, **Then** the verifier is version-aware and both outcomes are correct.

### User Story 4 - Honest protection & capability reporting (Priority: P2)

As the operator, the app tells me the truth about my key: whether it is hardware-backed, non-exportable, and user-presence-gated — and degrades honestly on a simulator or web build where no Secure Enclave exists.

**Why this priority**: The project's honesty discipline requires the app never claim hardware backing it does not have.

**Independent Test**: Inspect the Settings protection panel on (a) a physical Secure-Enclave device and (b) a simulator/web build; confirm (a) reports real enclave values and (b) reports a clearly non-production, non-hardware-backed state.

**Acceptance Scenarios**:

1. **Given** the app runs on a physical Secure-Enclave device, **When** the operator opens Settings, **Then** the protection panel reports `hardwareBacked: true`, `userPresenceRequired: true`, `privateKeyExportable: false`, `productionReady: true`, sourced from the native layer.
2. **Given** the app runs on a simulator or web build with no Secure Enclave, **When** the operator opens Settings, **Then** the panel honestly reports a non-hardware-backed development state and the build is marked non-production.

### User Story 5 - Beta distribution on a real device (Priority: P3)

As the operator, I can install and run the beta on a physical Secure-Enclave iPhone (and, where the Apple account permits, via TestFlight) so I can begin beta testing.

**Why this priority**: "Beta-testable" is the deliverable, but it depends on US1–US3 being real first.

**Independent Test**: Build and install the app on the paired physical device with a valid signing identity and complete US1–US3 end-to-end against a reachable gateway.

**Acceptance Scenarios**:

1. **Given** a configured signing identity, **When** the iOS app is built and installed on the physical device, **Then** it launches and the operator can pair, approve with Face ID, and see proofs verify.
2. **Given** the Apple account and environment permit, **When** an archive is uploaded to TestFlight, **Then** internal testers can install it; otherwise the build stops at a documented archive-ready / on-device-install state with the exact remaining steps.

### Edge Cases

- Biometric is unavailable (no enrolment, lockout) when a decision must be signed.
- The Secure Enclave is unavailable (simulator/web, or an older device) — the app must not fall back to an exportable key while still claiming `mobile_signed` hardware backing.
- The gateway is unreachable (loopback URL on a physical device; tailnet down) when a clearance is pending.
- The pinned tower key does not match a later proof's `key_id` (rotation or a different tower).
- A proof's `expires_at` differs by encoding (e.g. `Z` vs `+00:00`) from a re-derived value — the app must verify against the tower-returned value verbatim.
- A decision is attempted after expiry; a duplicate decision id is submitted.
- The realtime stream drops mid-session and must reconnect without losing pending clearances.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST provide an iOS runner project that builds and launches on a physical Secure-Enclave device.
- **FR-002**: On iOS, the app MUST generate the device signing key inside the Secure Enclave as a non-exportable key, via a native platform channel; it MUST NOT persist or be able to read private key bytes.
- **FR-003**: The signing key MUST be bound to user presence so that each signature requires biometric (Face ID/Touch ID) or device-credential authentication; the app MUST declare `NSFaceIDUsageDescription`.
- **FR-004**: Pairing MUST send the enclave public key and a real possession proof signed by the enclave key, and MUST use the operator-pinned `clearance_channel` from the pairing session; the app MUST NOT attempt to self-declare or upgrade its channel class.
- **FR-005**: The app MUST pin the tower public key per `tower_id` at pairing (trust-on-first-use) and resolve it by `proof.key_id` for proof verification.
- **FR-006**: Each device-authenticated request MUST carry a valid HMCP request signature (`HMCP-SIGN-V1` canonical string) produced by the enclave key; for approval decisions this signature MUST be produced behind the biometric gate.
- **FR-007**: The app MUST submit a real per-decision signature over the decision `signed_payload` (replacing the current hardcoded placeholder), computed by the enclave key behind the biometric gate, even though the gateway does not yet independently verify this field.
- **FR-008**: The app MUST implement an `ACT-CLEARANCE-PROOF-V1` verifier (see Conformance Requirements) and MUST fail closed, refusing to present a clearance as granted when verification fails.
- **FR-009**: The app MUST render only the ACT-composed `operator_message`/notification text for a clearance and MUST NOT display raw aircraft-supplied text.
- **FR-010**: The app MUST handle approve, deny, expire, cancel, and one-time consumption correctly, reflecting the gateway's terminal state and never broadening a decision's scope.
- **FR-011**: The app MUST source its protection state (hardware-backed, user-presence, exportable, production-ready) from the native layer and report it truthfully; on a simulator/web build with no Secure Enclave it MUST report a non-hardware-backed, non-production state.
- **FR-012**: The app MUST receive clearances over the existing realtime channel; it MUST NOT weaken the existing WebSocket auth model.
- **FR-013**: The gateway URL MUST remain operator-configurable so a physical device can reach a tailnet/LAN gateway instead of loopback.
- **FR-014**: A non-Secure-Enclave (simulator/web/dev) signing path MAY exist for development but MUST be clearly marked non-production and MUST NEVER report as hardware-backed.
- **FR-015**: The app MUST provide a multi-clearance inbox/queue that lists multiple simultaneous pending clearances, keeps each one's identity/state distinct, and lets the operator act on each independently.
- **FR-016**: The gateway MUST additively accept ECDSA P-256 (secp256r1) device signatures for `mobile_signed` devices — recording the per-device key algorithm at enrolment and verifying the existing canonical signing string under that algorithm — WITHOUT changing the canonical string, weakening replay/nonce/window rules, or breaking the Ed25519 path (the 141-test baseline MUST stay green, with additive P-256 tests).

### Key Entities

- **Secure-Enclave Device Key**: A non-exportable P-256 (decision pending) key generated in and used only by the Secure Enclave, gated by user presence; the app holds only its public key and an opaque reference.
- **Pairing Possession Proof**: An enclave-signed value proving the device controls the enrolled key, sent at pairing completion.
- **Tower Trust Anchor**: The pinned tower public key (per `tower_id`) used to verify `ACT-CLEARANCE-PROOF-V1` signatures.
- **Clearance**: The canonical `act.clearance.v2` object (state, `params_fingerprint`, `capability`, `risk_family`, `short_code`, `expires_at`, `tower_id`, `proof`, …) the app verifies and acts on.
- **Clearance Proof**: The `ACT-CLEARANCE-PROOF-V1` object the app verifies fail-closed.
- **Protection Report**: The honest, native-sourced description of the key's backing surfaced in Settings.

### Safety Requirements

- **SR-001**: The private signing key MUST be non-exportable; the app MUST remove the exportable-key store, the `fromBase64` reconstruction, and the SharedPreferences key mirror on iOS.
- **SR-002**: Every approval/deny signature MUST require user presence (biometric or device credential); an ungated signing path MUST NOT exist on production builds.
- **SR-003**: The app MUST verify ACT's clearance proof and MUST fail closed on mismatch, missing fields, expiry, unknown tower key, or invalid signature.
- **SR-004**: The app MUST NOT report hardware-backed/non-exportable/user-presence status it does not actually have; a simulator/dev fallback MUST report honestly.
- **SR-005**: The app MUST honor the operator-pinned channel and MUST NOT route-derive, self-declare, or upgrade its clearance channel.
- **SR-006**: The app MUST display only ACT-composed/redacted operator text, never raw aircraft text.
- **SR-007**: Decisions MUST be one-time and scoped; the app MUST NOT silently broaden scope or resubmit consumed decisions.
- **SR-008**: The app MUST verify against tower-returned bound values (e.g. `expires_at`) verbatim rather than re-deriving them.

### Conformance Requirements

These mirror the published contract and MUST match ACT byte-for-byte. They are contract facts, not implementation choices.

- **CR-001 (HMCP request signature)**: Sign the canonical request string `"HMCP-SIGN-V1\n" + METHOD + "\n" + path(?query) + "\n" + timestamp + "\n" + nonce + "\n" + sha256(body)`, body serialized compact + sorted (`separators=(",",":")`, `sort_keys=True`), signature base64url no-pad, headers `X-HMCP-Device-Id/Timestamp/Nonce/Signature`; respect the 300s window and `(device_id, nonce)` replay rules. (`gateway/src/hermes_gateway/signing.py:35-53`, `conftest.py:78-135`)
- **CR-002 (proof canonical string)**: Verify Ed25519 over a UTF-8 string of exactly 9 lines joined by single `\n` with NO trailing newline, in order: `ACT-CLEARANCE-PROOF-V1`, `approval_id`, `params_fingerprint`, `short_code`, `risk_family`, `expires_at`, `tower_id`, `contract_version`, `extensions_digest`. (`clearance_contract.py:157-170`)
- **CR-003 (derived fields)**: `params_fingerprint` = lowercase sha256 hexdigest of canonical JSON `{"extensions":…, "payload_redacted":…}`; `extensions_digest` = sha256 hexdigest of canonical JSON of the extensions object alone (empty = sha256 of `"{}"`); `short_code` = first 10 hex chars of `sha256("{approval_id}:{params_fingerprint}")`, uppercased. Canonical JSON = `sort_keys=True, separators=(",",":")` — a byte-exact Dart canonicalizer is required (Dart `jsonEncode` does not sort keys).
- **CR-004 (encoding/algorithm checks)**: Signature base64url WITHOUT padding; reject unless `proof.algorithm == "Ed25519"` and `proof.canonicalization == "ACT-CLEARANCE-PROOF-V1"`. `proof.signed_at` and `proof.fields` are advisory and NOT part of the signed string.
- **CR-005 (capability out-of-band)**: `capability` is required+core in v2 but is NOT bound into the signature; the app MUST compare it out-of-band against the pending request.
- **CR-006 (version awareness)**: Verify the committed v1 `test-vector.json` AND a live v2 proof correctly.
- **CR-007 (channel enrolment)**: Conform to ACT-003.1.1 — channel is operator-pinned at `/v1/pairing/start` and enforced from the authenticated principal; the device cannot supply or change it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a physical Secure-Enclave device, 100% of approval/deny signatures require a successful user-presence (biometric) authentication; there is no code path that signs without it on a production build.
- **SC-002**: The app cannot read or export the private signing key on iOS (verified by code inspection and the absence of any private-key read API).
- **SC-003**: 100% of valid proofs (committed v1 vector + a live v2 proof) verify VERIFIED, and 100% of mutated/expired/unknown-key/bad-signature proofs are rejected fail-closed.
- **SC-004**: A pending low-risk clearance can be approved end-to-end (request → realtime delivery → Face ID → signed decision → gateway resolves) against a live gateway, and a duplicate decision is rejected (409).
- **SC-005**: The Settings protection panel reports real enclave values on a physical device and an honest non-hardware-backed state on a simulator/web build.
- **SC-006**: Gateway pytest remains at 141 passing (plus any additive tests), `flutter analyze`/`flutter test` pass, ACT-001..007 behavior is unchanged, and `specify check` is green.
- **SC-007**: The verification matrix is published with every capability honestly classified across {code-complete | simulator-verified | real-device-verified | live-gateway-verified | TestFlight-distributed}; no row claims more than actually ran.

## Verification & Honesty

Every capability in this feature is tracked across five states, and reporting NEVER exceeds what actually ran:

- **code-complete** — written and reviewed; not executed.
- **simulator-verified** — ran on the iOS Simulator (no Secure Enclave; cannot prove hardware backing).
- **real-device-verified** — ran on the physical Secure-Enclave device. The hardware-backed-key row is "real-device-verified" ONLY if it signed inside the real Secure Enclave on hardware.
- **live-gateway-verified** — exercised against a running ACT gateway end-to-end.
- **TestFlight-distributed** — built, uploaded, and installable by testers via TestFlight.

A simulator/dev fallback path MUST NEVER be reported as hardware-backed.

## Non-Goals

- ~~Android / Keystore parity~~ — brought into scope 2026-06-19 (D6) as code-complete; see Android Keystore module. Real-hardware Android verification remains out of scope until a physical Android device is available.
- APNs push delivery (the gateway's `push_dispatch` is unavailable; the beta uses the existing realtime stream).
- High-risk mandatory families as the demo path, intervention (pause/stop/quarantine), Approve-Forever enforcement, and modified/conditional payloads.
- Changing the published clearance contract, proof format, canonical signing string, channel policy, or capability registry.
- **Hardware attestation of clearance-key origin** (ACT-003.2 residual — explicitly out of scope; running an enclave key on a real device is validation, attesting its provenance to the tower is the residual).
- The AgenticKVM mirror migration (ACT-003.2 residual — owned elsewhere).

## Assumptions

- The primary user is the operator of a self-hosted ACT gateway, reachable over Tailscale/LAN.
- A physical Secure-Enclave iPhone and Xcode are available for real-device verification; Flutter must be installed to build (see Decisions Pending).
- The tower public key is obtained out-of-band at pairing and pinned trust-on-first-use per `tower_id`; production key rotation behavior is to be confirmed.
- The gateway accepts the device's signature algorithm (see Decisions Pending — this determines whether a real Secure Enclave key is possible without a gateway change).

## Decisions (resolved 2026-06-19)

- **D1 — Key algorithm vs. no-backend-regression (the crux): Option A — additive gateway P-256.** The gateway is additively taught to verify **ECDSA P-256** device signatures for `mobile_signed` devices: the per-device key algorithm is recorded at enrolment, the canonical signing *string* is unchanged, and the Ed25519 path is fully preserved so the 141-test baseline stays green (new P-256 tests added). This yields a **real** Secure-Enclave key — the mission headline.
- **D2 — Build/verify environment: agent builds here.** Flutter is installed on this Mac; the agent scaffolds `mobile/ios/`, builds, and deploys to the paired physical iPhone for real-device + live-gateway verification. The operator performs only the interactive Apple signing-identity selection (and TestFlight 2FA later).
- **D3 — Apple beta path: free/personal on-device first, then TestFlight.** Stage 1 uses free personal-team provisioning to install on the physical device (achieves real-device + live-gateway verification without a paid account). Stage 2 (TestFlight) follows with the operator's paid Apple Developer account and interactive 2FA. Team id and bundle id confirmed out-of-band.
- **D4 — Test gateway endpoint.** Real-device + live-gateway verification uses an operator-provided reachable gateway host (Tailscale/LAN); the gateway URL is operator-configurable in the app. (Value confirmed out-of-band.)
- **D5 — Beta MVP feature set: core loop + multi-clearance queue.** The core loop (pair with hardware key → receive a low-risk clearance → Face-ID-approve with a real enclave signature → verify ACT's proof fail-closed → signed decision back, over the realtime stream) **plus a multi-clearance inbox/queue** handling multiple simultaneous pending clearances. APNs push, `local_terminal` UI, intervention/pause-stop, Approve-Forever, and modified payloads remain deferred (Non-Goals).
- **D6 — Platform scope updated 2026-06-19: iOS + Android.** Android was initially deferred, but the operator installed the Android SDK, so Android Keystore signing was brought in as **code-complete** parity: a non-exportable ECDSA P-256 key in the Android Keystore (StrongBox-preferred, TEE fallback) with `setUserAuthenticationRequired`, signing gated by `BiometricPrompt`, on the same `act/secure_enclave` MethodChannel. The APK builds. iOS remains the priority; real-hardware Android verification (StrongBox/TEE) needs a physical Android device (none present).

## Open Questions

- Should biometric gate every signed request or only authority-granting decisions (GETs vs. approvals)?
- Is a device-credential fallback acceptable when biometrics are unavailable, or must signing be biometric-only?
- How does the tower public key rotate in production, and how should pinned clients recover (re-pair)?
- Should a v2 conformance proof vector be committed, or is live-gateway verification sufficient for beta?

## Related References

- [Hermes Mobile Control Plane spec](../001-hermes-mobile-command/spec.md)
- [TUI/TUA/Advanced Approval UX spec](../002-tui-tua-ux/spec.md)
- [Clearance contract + proof format](../../contracts/clearance/)
- [Clearance channel policy](../../docs/security/clearance-channel-policy.md)
- [ACT-003 security hardening](../../docs/implementation/act-003-security-hardening.md)
- [ACT-003.1 authority-core hardening](../../docs/implementation/act-003-1-authority-core-hardening.md)
- [ACT-003.2 canonical clearance contract](../../docs/implementation/act-003-2-canonical-clearance-contract.md)
