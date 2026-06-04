import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../config/gateway_config.dart';
import '../security/device_request_signer.dart';

class GatewayApiClient {
  GatewayApiClient({
    required this.config,
    required this.signer,
    HttpClient? httpClient,
  }) : _httpClient = httpClient ?? HttpClient();

  final GatewayConfig config;
  final DeviceRequestSigner signer;
  final HttpClient _httpClient;

  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, String?> query = const {},
    bool signed = true,
  }) async {
    return _sendJson(
      method: 'GET',
      path: path,
      query: query,
      signed: signed,
    );
  }

  Future<Map<String, dynamic>> postJson(
    String path, {
    Map<String, Object?> body = const {},
    Map<String, String?> query = const {},
    bool signed = true,
  }) async {
    return _sendJson(
      method: 'POST',
      path: path,
      query: query,
      body: body,
      signed: signed,
    );
  }

  Future<Map<String, dynamic>> _sendJson({
    required String method,
    required String path,
    Map<String, String?> query = const {},
    Map<String, Object?> body = const {},
    required bool signed,
  }) async {
    final uri = config.resolve(path, query);
    final bodyBytes = method == 'GET'
        ? Uint8List(0)
        : Uint8List.fromList(utf8.encode(jsonEncode(_withoutNullValues(body))));
    final request = await _httpClient.openUrl(method, uri);
    request.headers.contentType = ContentType.json;

    if (signed) {
      final pathWithQuery = uri.hasQuery ? '${uri.path}?${uri.query}' : uri.path;
      final signedHeaders = await signer.sign(
        method: method,
        pathWithQuery: pathWithQuery,
        body: bodyBytes,
      );
      for (final entry in signedHeaders.values.entries) {
        request.headers.set(entry.key, entry.value);
      }
    }

    if (bodyBytes.isNotEmpty) {
      request.add(bodyBytes);
    }
    final response = await request.close();
    final responseText = await response.transform(utf8.decoder).join();
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw GatewayApiException(
        statusCode: response.statusCode,
        body: responseText,
      );
    }
    if (responseText.isEmpty) {
      return const {};
    }
    return jsonDecode(responseText) as Map<String, dynamic>;
  }
}

class GatewayApiException implements Exception {
  const GatewayApiException({
    required this.statusCode,
    required this.body,
  });

  final int statusCode;
  final String body;

  @override
  String toString() => 'GatewayApiException($statusCode): $body';
}

Map<String, Object?> _withoutNullValues(Map<String, Object?> body) {
  return {
    for (final entry in body.entries)
      if (entry.value != null) entry.key: entry.value,
  };
}
