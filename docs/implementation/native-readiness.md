# Native Readiness

Sprint: `HERMES-MCP-MOBILE-NATIVE-REALTIME-003`

Last checked again during `HERMES-MCP-PLATFORM-CONSOLIDATION-006` on 2026-06-06.

## Current Host State

The local host can run the Flutter app on Chrome and exposes macOS as a listed
desktop target, but native iOS and Android targets are not ready.

Observed tool state:

- Flutter: `3.44.1` stable at `/opt/homebrew/share/flutter`
- Dart: `3.12.1`
- Chrome: available
- Connected Flutter targets: `Chrome`, `macOS`
- Android SDK: missing
- `sdkmanager`: unavailable
- `adb`: unavailable
- Java runtime: unavailable
- Xcode: command line tools are selected; full Xcode is not installed or not selected
- CocoaPods: unavailable

`flutter doctor -v` reports Android SDK missing and Xcode/CocoaPods incomplete.
`xcodebuild -version` fails because the active developer directory is
`/Library/Developer/CommandLineTools`.

## Minimum Supported Flutter Targets

Current development validation target:

- Chrome web target

Targets expected after native setup:

- iOS simulator
- iOS physical device
- Android emulator
- Android physical device

macOS desktop is listed by Flutter, but the project is still mobile-first and
macOS is treated as a local validation convenience rather than a release target.

## iOS Setup Steps

1. Install full Xcode from Apple.
2. Select the full Xcode developer directory:

   ```bash
   sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
   ```

3. Complete Xcode first-launch setup:

   ```bash
   sudo xcodebuild -runFirstLaunch
   ```

4. Install CocoaPods:

   ```bash
   brew install cocoapods
   ```

5. Re-check Flutter:

   ```bash
   flutter doctor -v
   flutter devices
   ```

6. Launch a simulator from Xcode or with `open -a Simulator`, then run:

   ```bash
   cd mobile
   flutter run -d ios
   ```

## Android Setup Steps

1. Install Android Studio.
2. Use Android Studio first launch to install:
   - Android SDK
   - Android SDK Platform Tools
   - Android SDK Command-line Tools
   - At least one emulator image
3. Install a Java runtime if Android Studio did not provide one on `PATH`.
4. If Flutter cannot find the SDK, configure it explicitly:

   ```bash
   flutter config --android-sdk /path/to/Android/sdk
   ```

5. Accept Android SDK licenses:

   ```bash
   flutter doctor --android-licenses
   ```

6. Re-check Flutter:

   ```bash
   flutter doctor -v
   flutter devices
   ```

7. Start an emulator or connect a device, then run:

   ```bash
   cd mobile
   flutter run -d android
   ```

## Native Readiness Decision

No destructive or system-level changes were made during this sprint. The app
continues to validate on Chrome while native setup remains an environment task.
The mobile code now includes a platform-aware secure storage abstraction using
`flutter_secure_storage` where native platforms support it and an explicit
SharedPreferences fallback for web/development. Native iOS Keychain and Android
Keystore behavior still need validation once the iOS and Android toolchains are
available.
