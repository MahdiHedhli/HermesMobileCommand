import 'package:shared_preferences/shared_preferences.dart';

abstract class SecureKeyStore {
  Future<String?> readDeviceId();
  Future<String?> readAccessToken();
  Future<String?> readRefreshToken();
  Future<String?> readDevicePrivateKey();
  Future<String?> readDevicePublicKey();
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
