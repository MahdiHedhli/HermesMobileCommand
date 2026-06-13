import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'device_request_signer.dart';

abstract class SecureKeyStore {
  Future<String?> readDeviceId();
  Future<String?> readAccessToken();
  Future<String?> readRefreshToken();
  Future<String?> readDevicePrivateKey();
  Future<String?> readDevicePublicKey();
  Future<String> storageWarning();
  Future<ClearanceKeyProtection> clearanceKeyProtection();
  Future<void> saveDeviceKeyPair({
    required String privateKey,
    required String publicKey,
  });
  Future<void> saveDeviceSession({
    required String deviceId,
    required String accessToken,
    required String refreshToken,
  });
  Future<void> clear();
}

class PlatformAwareSecureKeyStore implements SecureKeyStore {
  PlatformAwareSecureKeyStore(this.preferences)
      : _fallback = SharedPreferencesSecureKeyStore(preferences);

  final SharedPreferences preferences;
  final SharedPreferencesSecureKeyStore _fallback;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  bool get _useFallback => kIsWeb;

  @override
  Future<String?> readAccessToken() => _read(_accessTokenKey);

  @override
  Future<String?> readDeviceId() => _fallback.readDeviceId();

  @override
  Future<String?> readDevicePrivateKey() => _read(_devicePrivateKeyKey);

  @override
  Future<String?> readDevicePublicKey() => _read(_devicePublicKeyKey);

  @override
  Future<String?> readRefreshToken() => _read(_refreshTokenKey);

  @override
  Future<String> storageWarning() async {
    if (_useFallback) {
      return 'Web/dev fallback storage active; private key is not in native secure storage.';
    }
    return 'Native secure storage enabled for device secrets.';
  }

  @override
  Future<ClearanceKeyProtection> clearanceKeyProtection() async {
    if (_useFallback) {
      return ClearanceKeyProtection.developmentExportableEd25519;
    }
    return const ClearanceKeyProtection(
      backend: 'flutter_secure_storage_exportable_ed25519',
      hardwareBacked: null,
      userPresenceRequired: false,
      privateKeyExportable: true,
      productionReady: false,
      warning:
          'Native secure storage protects bytes at rest, but signing is not yet non-exportable or user-presence gated.',
    );
  }

  @override
  Future<void> saveDeviceKeyPair({
    required String privateKey,
    required String publicKey,
  }) async {
    await _write(_devicePrivateKeyKey, privateKey);
    await _write(_devicePublicKeyKey, publicKey);
  }

  @override
  Future<void> saveDeviceSession({
    required String deviceId,
    required String accessToken,
    required String refreshToken,
  }) async {
    await _fallback.saveDeviceSession(
      deviceId: deviceId,
      accessToken: accessToken,
      refreshToken: refreshToken,
    );
    await _write(_accessTokenKey, accessToken);
    await _write(_refreshTokenKey, refreshToken);
  }

  @override
  Future<void> clear() async {
    await _fallback.clear();
    if (_useFallback) {
      return;
    }
    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
    await _secureStorage.delete(key: _devicePrivateKeyKey);
    await _secureStorage.delete(key: _devicePublicKeyKey);
  }

  Future<String?> _read(String key) async {
    if (_useFallback) {
      return _fallback.preferences.getString(key);
    }
    try {
      return await _secureStorage.read(key: key);
    } on Object {
      return _fallback.preferences.getString(key);
    }
  }

  Future<void> _write(String key, String value) async {
    await _fallback.preferences.setString(key, value);
    if (_useFallback) {
      return;
    }
    try {
      await _secureStorage.write(key: key, value: value);
    } on Object {
      // SharedPreferences remains the explicit development fallback.
    }
  }
}

class SharedPreferencesSecureKeyStore implements SecureKeyStore {
  const SharedPreferencesSecureKeyStore(this.preferences);

  final SharedPreferences preferences;

  @override
  Future<String?> readAccessToken() async =>
      preferences.getString(_accessTokenKey);

  @override
  Future<String?> readDeviceId() async => preferences.getString(_deviceIdKey);

  @override
  Future<String?> readDevicePrivateKey() async =>
      preferences.getString(_devicePrivateKeyKey);

  @override
  Future<String?> readDevicePublicKey() async =>
      preferences.getString(_devicePublicKeyKey);

  @override
  Future<String> storageWarning() async =>
      'Development fallback storage active; private key is not in native secure storage.';

  @override
  Future<ClearanceKeyProtection> clearanceKeyProtection() async =>
      ClearanceKeyProtection.developmentExportableEd25519;

  @override
  Future<String?> readRefreshToken() async =>
      preferences.getString(_refreshTokenKey);

  @override
  Future<void> saveDeviceKeyPair({
    required String privateKey,
    required String publicKey,
  }) async {
    await preferences.setString(_devicePrivateKeyKey, privateKey);
    await preferences.setString(_devicePublicKeyKey, publicKey);
  }

  @override
  Future<void> saveDeviceSession({
    required String deviceId,
    required String accessToken,
    required String refreshToken,
  }) async {
    await preferences.setString(_deviceIdKey, deviceId);
    await preferences.setString(_accessTokenKey, accessToken);
    await preferences.setString(_refreshTokenKey, refreshToken);
  }

  @override
  Future<void> clear() async {
    await preferences.remove(_deviceIdKey);
    await preferences.remove(_accessTokenKey);
    await preferences.remove(_refreshTokenKey);
    await preferences.remove(_devicePrivateKeyKey);
    await preferences.remove(_devicePublicKeyKey);
  }
}

class InMemorySecureKeyStore implements SecureKeyStore {
  String? _deviceId;
  String? _accessToken;
  String? _refreshToken;
  String? _devicePrivateKey;
  String? _devicePublicKey;

  @override
  Future<String?> readAccessToken() async => _accessToken;

  @override
  Future<String?> readDeviceId() async => _deviceId;

  @override
  Future<String?> readDevicePrivateKey() async => _devicePrivateKey;

  @override
  Future<String?> readDevicePublicKey() async => _devicePublicKey;

  @override
  Future<String> storageWarning() async => 'In-memory test storage active.';

  @override
  Future<ClearanceKeyProtection> clearanceKeyProtection() async =>
      ClearanceKeyProtection.developmentExportableEd25519;

  @override
  Future<String?> readRefreshToken() async => _refreshToken;

  @override
  Future<void> saveDeviceKeyPair({
    required String privateKey,
    required String publicKey,
  }) async {
    _devicePrivateKey = privateKey;
    _devicePublicKey = publicKey;
  }

  @override
  Future<void> saveDeviceSession({
    required String deviceId,
    required String accessToken,
    required String refreshToken,
  }) async {
    _deviceId = deviceId;
    _accessToken = accessToken;
    _refreshToken = refreshToken;
  }

  @override
  Future<void> clear() async {
    _deviceId = null;
    _accessToken = null;
    _refreshToken = null;
    _devicePrivateKey = null;
    _devicePublicKey = null;
  }
}

const _deviceIdKey = 'hmcp.device.id';
const _accessTokenKey = 'hmcp.device.access_token';
const _refreshTokenKey = 'hmcp.device.refresh_token';
const _devicePrivateKeyKey = 'hmcp.device.private_key';
const _devicePublicKeyKey = 'hmcp.device.public_key';
