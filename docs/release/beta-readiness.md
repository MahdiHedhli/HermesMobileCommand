# Beta Readiness Assessment

Sprint: `HERMES-MCP-PLATFORM-CONSOLIDATION-006`

Current product identity: Agentic Control Tower (ACT). Hermes remains adapter
#1 and is still the real backend integration path that must prove the next beta
gate.

Ratings:

- Ready: Suitable for beta scope with expected polish and monitoring.
- Needs Work: Concept and thin implementation exist, but beta risk remains.
- Not Started: No meaningful beta-ready implementation yet.

## Scorecard

| Area | Capability | Rating | Notes |
| --- | --- | --- | --- |
| Identity | Pairing | Ready | Device-key pairing exists and supports local gateway flows. |
| Identity | Device lifecycle | Needs Work | Devices can be registered and revoked, but lifecycle UX and recovery need polish. |
| Identity | Key rotation | Needs Work | Contract includes rotation direction, but native app rotation flow is not beta-ready. |
| Identity | Multi-device support | Needs Work | The model allows it; UX and conflict handling need more work. |
| Security | Ed25519 request signing | Ready | Sensitive mobile decisions use canonical signed requests. |
| Security | Replay protection | Ready | Timestamp and nonce checks are in place for signed request paths. |
| Security | WebSocket auth | Needs Work | Event streaming works; all sensitive streams need consistent signed or tokenized attach semantics. |
| Security | TUI hardening | Needs Work | Local PTY is disabled by default and gated, but shell sandboxing and production isolation are not complete. |
| Security | Audit coverage | Ready | Major approval, notification, operator session, voice, and assistance paths emit audit events. |
| Security | Capability grants | Needs Work | TUI grants exist as controls, but a first-class grant model is needed before beta. |
| Mobile | Chrome/web target | Ready | Validated for local development and screenshots. |
| Mobile | iPhone | Needs Work | Xcode toolchain is incomplete on this host. |
| Mobile | iPad | Needs Work | UI needs split-layout validation and native target testing. |
| Mobile | Android | Needs Work | Android SDK is missing on this host. |
| Mobile | Secure storage | Needs Work | Abstraction exists; native storage must be validated on iOS/Android. |
| Operator Experience | Clearances | Ready | Signed grant/deny and advanced responses are implemented. UX grouping needs polish. |
| Operator Experience | TUA | Needs Work | Backend and UI are present, but mission context and lifecycle consistency need cleanup. |
| Operator Experience | TUI | Needs Work | Prototype is functional in dev mode only. |
| Operator Experience | Browser Assistance | Needs Work | Thin note/return-control model works; no live browser stream/control yet. |
| Operator Experience | Voice | Needs Work | Text-backed MVP works; no native audio or streaming. |
| Hermes Integration | Notification flow | Ready | Hermes adapter creates durable notification, event, and audit records. |
| Hermes Integration | Clearance flow | Ready | Hermes adapter creates pending clearances through compatibility approval records and mobile can resolve them. |
| Hermes Integration | Assistance flow | Needs Work | TUA/browser assistance exist, but real Hermes runtime handoff is still thin. |
| Fleet Operations | Multi-agent inventory | Needs Work | Agent/node listing exists; fleet operations and durable mission management need more depth. |

## Native Readiness Findings

Host checks were run during this sprint.

| Check | Result |
| --- | --- |
| `flutter doctor -v` | Flutter 3.44.1 is available. Chrome and macOS targets are available. Android toolchain is missing. Xcode is incomplete because the active developer directory is Command Line Tools. CocoaPods is missing. |
| `xcodebuild -version` | Fails because full Xcode is not selected or installed. |
| `pod --version` | `pod` command is not available. |
| `java -version` | No Java runtime is available. |
| `sdkmanager` / `adb` | Not available. |

Minimum currently validated target:

- Chrome web target for local development.

Minimum target needed before beta:

- iOS simulator or physical iPhone with full Xcode and CocoaPods.
- Android emulator or physical Android device with Android SDK, platform tools, and Java.

## Beta Entry Criteria

Identity:

- Pairing, reset pairing, revocation, and key rotation are usable from Settings.
- Device status clearly shows paired/unpaired, storage backend, and last gateway verification.

Security:

- All sensitive HTTP routes and WebSocket attach paths use signed-device or short-lived signed-token controls.
- TUI remains disabled unless explicitly configured.
- Capability grants are visible, revocable, and audited.
- Audit log has documented retention and export behavior.

Mobile:

- iPhone and Android builds pass analyzer/tests and launch on native targets.
- Secure storage works on iOS Keychain and Android Keystore.
- iPad layout is at least usable for Home, Agents, Inbox, Approval Detail, TUI, and TUA.

Operator Experience:

- Approval Detail has sticky primary actions.
- More menu actions are grouped by intent.
- Operator sessions are discoverable from Home, Agents, Missions, and Inbox.
- Browser Assistance and Voice clearly distinguish real, simulated, and planned behavior.

Hermes Integration:

- Real Hermes runtime uses mobile_notify and approval_requested adapters.
- Assistance return-control summaries are consumable by Hermes.
- Gateway binding controls are documented and tested for local and Tailscale modes.

## Overall Rating

Beta readiness: Needs Work.

The platform is coherent and strong enough to continue toward beta, but native validation, capability grants, operator session consolidation, and real Hermes runtime handoff are the blocking categories.
