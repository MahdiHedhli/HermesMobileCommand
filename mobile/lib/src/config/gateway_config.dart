import 'package:shared_preferences/shared_preferences.dart';

class GatewayConfig {
  const GatewayConfig({
    required this.baseUrl,
  });

  final Uri baseUrl;

  static final loopback = GatewayConfig(
    baseUrl: Uri.parse('http://127.0.0.1:8787/v1'),
  );

  static GatewayConfig fromInput(String value) {
    final trimmed = value.trim();
    final parsed = Uri.parse(trimmed);
    final path =
        parsed.path.isEmpty || parsed.path == '/' ? '/v1' : parsed.path;
    return GatewayConfig(baseUrl: parsed.replace(path: path));
  }

  Uri resolve(String path, [Map<String, String?> query = const {}]) {
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    final basePath =
        baseUrl.path.endsWith('/') ? baseUrl.path : '${baseUrl.path}/';
    final queryParameters = <String, String>{};
    for (final entry in query.entries) {
      if (entry.value != null) {
        queryParameters[entry.key] = entry.value!;
      }
    }
    final resolved = baseUrl.replace(path: '$basePath$cleanPath');
    if (queryParameters.isEmpty) {
      return resolved;
    }
    return resolved.replace(queryParameters: queryParameters);
  }
}

abstract class GatewayConfigStore {
  Future<GatewayConfig> read();
  Future<void> save(GatewayConfig config);
}

class SharedPreferencesGatewayConfigStore implements GatewayConfigStore {
  const SharedPreferencesGatewayConfigStore(this.preferences);

  final SharedPreferences preferences;

  @override
  Future<GatewayConfig> read() async {
    final value = preferences.getString(_gatewayBaseUrlKey);
    if (value == null || value.trim().isEmpty) {
      return GatewayConfig.loopback;
    }
    return GatewayConfig.fromInput(value);
  }

  @override
  Future<void> save(GatewayConfig config) async {
    await preferences.setString(_gatewayBaseUrlKey, config.baseUrl.toString());
  }
}

class InMemoryGatewayConfigStore implements GatewayConfigStore {
  InMemoryGatewayConfigStore({GatewayConfig? initial})
      : _config = initial ?? GatewayConfig.loopback;

  GatewayConfig _config;

  @override
  Future<GatewayConfig> read() async => _config;

  @override
  Future<void> save(GatewayConfig config) async {
    _config = config;
  }
}

const _gatewayBaseUrlKey = 'hmcp.gateway.base_url';
