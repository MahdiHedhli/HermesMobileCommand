abstract class SecureKeyStore {
  Future<String?> readDeviceId();
  Future<String?> readAccessToken();
  Future<String?> readRefreshToken();
  Future<void> saveDeviceSession({
    required String deviceId,
    required String accessToken,
    required String refreshToken,
  });
  Future<void> clear();
}

class InMemorySecureKeyStore implements SecureKeyStore {
  String? _deviceId;
  String? _accessToken;
  String? _refreshToken;

  @override
  Future<String?> readAccessToken() async => _accessToken;

  @override
  Future<String?> readDeviceId() async => _deviceId;

  @override
  Future<String?> readRefreshToken() async => _refreshToken;

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
  }
}
