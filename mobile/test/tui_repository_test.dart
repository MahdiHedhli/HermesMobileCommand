import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile_control_plane/src/api/gateway_api_client.dart';
import 'package:hermes_mobile_control_plane/src/config/gateway_config.dart';
import 'package:hermes_mobile_control_plane/src/repositories/tui_repository.dart';
import 'package:hermes_mobile_control_plane/src/security/device_request_signer.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('create session posts signed gateway request', () async {
    late http.Request captured;
    final client = GatewayApiClient(
      config: GatewayConfig.fromInput('http://127.0.0.1:8787/v1'),
      signer: const _StaticSigner(),
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(jsonEncode(_sessionJson()), 201);
      }),
    );

    final session = await TuiRepository(client).createSession(
      agentId: 'agent_mock',
      sessionContextId: 'sess_mock',
    );

    final body = jsonDecode(captured.body) as Map<String, dynamic>;
    expect(captured.method, 'POST');
    expect(captured.url.path, '/v1/tui/sessions');
    expect(captured.headers['X-HMCP-Device-Id'], 'dev_test');
    expect(body['agent_id'], 'agent_mock');
    expect(body['session_context_id'], 'sess_mock');
    expect(session.sessionId, 'tui_1');
    expect(session.state, 'active');
  });

  test('close session unwraps control response', () async {
    final client = GatewayApiClient(
      config: GatewayConfig.fromInput('http://127.0.0.1:8787/v1'),
      signer: const _StaticSigner(),
      httpClient: MockClient((request) async {
        return http.Response(
          jsonEncode({'session': _sessionJson(state: 'closed')}),
          200,
        );
      }),
    );

    final session = await TuiRepository(client).close('tui_1');

    expect(session.state, 'closed');
  });
}

class _StaticSigner implements DeviceRequestSigner {
  const _StaticSigner();

  @override
  Future<SignedRequestHeaders> sign({
    required String method,
    required String pathWithQuery,
    required Uint8List body,
  }) async {
    return const SignedRequestHeaders({
      'X-HMCP-Device-Id': 'dev_test',
      'X-HMCP-Timestamp': '1',
      'X-HMCP-Nonce': 'nonce-test',
      'X-HMCP-Signature': 'signature-test',
    });
  }
}

Map<String, dynamic> _sessionJson({String state = 'active'}) {
  return {
    'session_id': 'tui_1',
    'agent_id': 'agent_mock',
    'node_id': 'node_test',
    'user_device_id': 'dev_test',
    'state': state,
    'command': '/bin/cat',
    'working_directory': '/tmp',
    'created_at': '2026-06-05T12:00:00Z',
    'last_activity_at': '2026-06-05T12:00:01Z',
    'closed_at': state == 'closed' ? '2026-06-05T12:00:02Z' : null,
    'risk_level': 'high',
    'audit_refs': ['aud_1'],
  };
}
