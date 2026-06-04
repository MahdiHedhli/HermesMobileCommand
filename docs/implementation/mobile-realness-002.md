# Mobile Realness 002

Sprint: `HERMES-MCP-MOBILE-REALNESS-002`

This slice turns the Flutter alpha into a locally runnable app that can pair with a local Hermes Gateway, read gateway-backed data, and approve a real pending approval with signed device requests.

## What Changed

- Installed/configured Flutter SDK locally through Homebrew.
- Added Flutter web scaffold so the app can run on the available Chrome target.
- Replaced the mobile API client with a cross-platform `package:http` client.
- Added Ed25519 mobile request signing compatible with gateway `HMCP-SIGN-V1`.
- Added persisted local gateway base URL configuration.
- Added persisted local-dev device key/session storage using `shared_preferences`.
- Added minimal pairing UX in Settings.
- Added signed approve/deny execution from Approval Detail.
- Added loopback-only gateway CORS support for Flutter web local development.
- Added a local demo gateway runner: `gateway/scripts/mobile_realness_demo.py`.

## Local Setup

From the repository root:

```bash
uv run --project gateway python gateway/scripts/mobile_realness_demo.py --port 8787
```

In another terminal:

```bash
cd mobile
flutter pub get
flutter run -d chrome --web-port 53711 --web-hostname 127.0.0.1
```

In the app:

1. Open Settings.
2. Confirm gateway URL is `http://127.0.0.1:8787/v1`.
3. Select Start under Pairing.
4. Select Complete.
5. Open Inbox.
6. Open the pending approval.
7. Select Approve or Deny.

## Screenshots

- [Home](screenshots/mobile-alpha/home.png)
- [Agents](screenshots/mobile-alpha/agents.png)
- [Inbox](screenshots/mobile-alpha/inbox-real.png)
- [Approval detail](screenshots/mobile-alpha/approval-detail.png)
- [Approval More modal](screenshots/mobile-alpha/approval-more-modal.png)
- [Approval approved](screenshots/mobile-alpha/approval-approved-fixed.png)
- [TUA](screenshots/mobile-alpha/tua.png)
- [TUI](screenshots/mobile-alpha/tui.png)

## Signing Compatibility

The mobile signer uses the same canonical format as the gateway:

```text
HMCP-SIGN-V1
METHOD
/v1/path?query=value
unix_timestamp_seconds
nonce
sha256_hex_body
```

The signature is Ed25519 over the UTF-8 canonical string. Public keys, private keys, signatures, and nonces are base64url encoded without padding. Signed requests include:

- `X-HMCP-Device-Id`
- `X-HMCP-Timestamp`
- `X-HMCP-Nonce`
- `X-HMCP-Signature`

## Demo Result

The Chrome run paired with the local demo gateway and approved approval `appr_uPGDE4-jAoQ2k_a-`.

Gateway verification:

```text
state=approved
selected_scope=once
audit_events=approval_requested, approval_decision
events=approval.requested pending, approval.resolved approved
```

## Simulator And Device Notes

`flutter doctor` found Chrome available. Android SDK and full Xcode were not configured, so the runnable target for this slice was Chrome web.

The current local-dev key store uses `shared_preferences`. This is acceptable for Chrome/simulator validation only. Production mobile builds still need platform secure storage backed by iOS Keychain and Android Keystore.

## Known Limitations

- TUA and TUI remain mock-backed repository surfaces.
- Approval More actions are still UX-only except primary Approve and Deny.
- Access/refresh tokens are persisted but not yet used for refresh flows.
- Flutter web local development requires loopback CORS; native iOS/Android over Tailscale will not need browser CORS.
- Browser screenshots were captured through Chrome remote debugging because the in-app browser wrapper could not reliably screenshot Flutter canvas output.
