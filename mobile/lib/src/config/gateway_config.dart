class GatewayConfig {
  const GatewayConfig({
    required this.baseUrl,
  });

  final Uri baseUrl;

  static final loopback = GatewayConfig(
    baseUrl: Uri.parse('http://127.0.0.1:8787/v1'),
  );

  Uri resolve(String path, [Map<String, String?> query = const {}]) {
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    final basePath = baseUrl.path.endsWith('/') ? baseUrl.path : '${baseUrl.path}/';
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
