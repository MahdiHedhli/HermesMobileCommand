import 'package:flutter_test/flutter_test.dart';
import 'package:agentic_control_tower/src/security/secure_key_store.dart';

void main() {
  test('in-memory secure store persists and clears pairing material', () async {
    final store = InMemorySecureKeyStore();

    await store.saveDeviceKeyPair(
      privateKey: 'private',
      publicKey: 'public',
    );
    await store.saveDeviceSession(
      deviceId: 'dev_1',
      accessToken: 'access',
      refreshToken: 'refresh',
    );

    expect(await store.readDeviceId(), 'dev_1');
    expect(await store.readDevicePrivateKey(), 'private');
    expect(await store.storageWarning(), contains('In-memory'));
    final protection = await store.clearanceKeyProtection();
    expect(protection.backend, 'development_exportable_ed25519');
    expect(protection.hardwareBacked, isFalse);
    expect(protection.userPresenceRequired, isFalse);
    expect(protection.productionReady, isFalse);

    await store.clear();

    expect(await store.readDeviceId(), isNull);
    expect(await store.readDevicePrivateKey(), isNull);
  });
}
