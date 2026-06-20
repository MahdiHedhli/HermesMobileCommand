import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:agentic_control_tower/src/api/gateway_api_client.dart';
import 'package:agentic_control_tower/src/config/gateway_config.dart';
import 'package:agentic_control_tower/src/models/alpha_models.dart';
import 'package:agentic_control_tower/src/repositories/agents_repository.dart';
import 'package:agentic_control_tower/src/repositories/approval_responses_repository.dart';
import 'package:agentic_control_tower/src/repositories/approvals_repository.dart';
import 'package:agentic_control_tower/src/repositories/browser_assistance_repository.dart';
import 'package:agentic_control_tower/src/repositories/dashboard_repository.dart';
import 'package:agentic_control_tower/src/repositories/gateway_alpha_repository.dart';
import 'package:agentic_control_tower/src/repositories/missions_repository.dart';
import 'package:agentic_control_tower/src/repositories/notifications_repository.dart';
import 'package:agentic_control_tower/src/repositories/tua_repository.dart';
import 'package:agentic_control_tower/src/repositories/voice_repository.dart';
import 'package:agentic_control_tower/src/security/device_request_signer.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('approval response repository posts modified response', () async {
    late http.Request captured;
    final repository = ApprovalResponsesRepository(_client((request) async {
      captured = request;
      return http.Response(jsonEncode(_approvalResponseJson()), 201);
    }));

    final response = await repository.modified(
      'appr_1',
      alternateDirective: 'Use dry-run mode.',
    );

    final body = jsonDecode(captured.body) as Map<String, dynamic>;
    expect(captured.url.path, '/v1/approvals/appr_1/responses');
    expect(body['decision_type'], 'modified');
    expect(response.decisionType, 'modified');
  });

  test('tua repository creates session and returns control', () async {
    final seenPaths = <String>[];
    final repository = TuaRepository(_client((request) async {
      seenPaths.add(request.url.path);
      return http.Response(jsonEncode(_assistanceSessionJson()), 201);
    }));

    final session = await repository.createSession(
      'tua_req_1',
      initialMessage: 'Opening from mobile.',
    );
    await repository.returnControl(
      session.assistanceSessionId,
      summary: 'Returned.',
    );

    expect(seenPaths, [
      '/v1/tua/requests/tua_req_1/sessions',
      '/v1/tua/sessions/tua_sess_1/return-control',
    ]);
  });

  test('gateway alpha repository surfaces real TUA requests as assistance '
      'inbox items and dedupes the agent_blocked notification', () async {
    final client = _client((request) async {
      final path = request.url.path;
      if (path == '/v1/approvals') {
        return http.Response(jsonEncode({'approvals': const []}), 200);
      }
      if (path == '/v1/notifications') {
        return http.Response(
          jsonEncode({
            'notifications': [_agentBlockedNotificationJson()],
          }),
          200,
        );
      }
      if (path == '/v1/tua/requests') {
        return http.Response(
          jsonEncode({
            'requests': [
              _assistanceRequestJson('tua_req_open', 'requested'),
              _assistanceRequestJson('tua_req_done', 'closed'),
            ],
          }),
          200,
        );
      }
      return http.Response('{}', 200);
    });
    final repository = GatewayAlphaRepository(
      dashboardRepository: DashboardRepository(client),
      agentsRepository: AgentsRepository(client),
      approvalsRepository: ApprovalsRepository(client),
      missionsRepository: MissionsRepository(client),
      notificationsRepository: NotificationsRepository(client),
      tuaRepository: TuaRepository(client),
    );

    final inbox = await repository.loadInbox();
    final assistance =
        inbox.where((item) => item.kind == InboxKind.assistance).toList();

    expect(
      assistance.length,
      1,
      reason: 'only the open TUA request becomes an assistance item — the '
          'closed request and the agent_blocked notification do not',
    );
    expect(
      assistance.single.id,
      'tua_req_open',
      reason: 'assistance item id must be the real TUA requestId so the TUA '
          'screen can open a real session',
    );
  });

  test('browser assistance repository records event', () async {
    late http.Request captured;
    final repository = BrowserAssistanceRepository(_client((request) async {
      captured = request;
      return http.Response(jsonEncode(_browserSessionJson()), 200);
    }));

    final session = await repository.recordEvent(
      'br_1',
      note: 'Reviewed.',
    );

    expect(captured.url.path, '/v1/browser-assistance/sessions/br_1/event');
    expect(session.browserSessionId, 'br_1');
  });

  test('voice repository creates text fallback message', () async {
    final seenPaths = <String>[];
    final repository = VoiceRepository(_client((request) async {
      seenPaths.add(request.url.path);
      if (request.url.path.endsWith('/messages')) {
        return http.Response(jsonEncode(_voiceMessageJson()), 201);
      }
      return http.Response(jsonEncode(_voiceSessionJson()), 201);
    }));

    final session = await repository.createSession();
    final message = await repository.sendMessage(
      session.voiceSessionId,
      body: 'Pause if risk increases.',
    );

    expect(seenPaths, [
      '/v1/voice/sessions',
      '/v1/voice/sessions/voice_1/messages',
    ]);
    expect(message.inputMode, 'text_fallback');
  });
}

GatewayApiClient _client(
  Future<http.Response> Function(http.Request) handler,
) {
  return GatewayApiClient(
    config: GatewayConfig.fromInput('http://127.0.0.1:8787/v1'),
    signer: const _StaticSigner(),
    httpClient: MockClient(handler),
  );
}

class _StaticSigner implements DeviceRequestSigner {
  const _StaticSigner();

  @override
  ClearanceKeyProtection get protection =>
      ClearanceKeyProtection.developmentExportableEd25519;

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

Map<String, dynamic> _approvalResponseJson() {
  return {
    'approval_response_id': 'ar_1',
    'approval_id': 'appr_1',
    'decision_type': 'modified',
    'created_by_device_id': 'dev_test',
    'constraints': [],
    'created_at': '2026-06-05T12:00:00Z',
  };
}

Map<String, dynamic> _assistanceRequestJson(String requestId, String state) {
  return {
    'request_id': requestId,
    'node_id': 'node_test',
    'agent_id': 'colpanic_m2',
    'session_id': 'sess_test',
    'reason': 'Should I deploy build 42 to production?',
    'state': state,
    'created_at': '2026-06-05T12:00:00Z',
    'updated_at': '2026-06-05T12:00:01Z',
  };
}

Map<String, dynamic> _agentBlockedNotificationJson() {
  return {
    'notification_id': 'notif_1',
    'category': 'agent_blocked',
    'urgency': 'high',
    'state': 'unread',
    'created_at': '2026-06-05T12:00:00Z',
    'title_safe': 'Agent blocked',
    'body_safe': 'Needs help',
    'agent_id': 'colpanic_m2',
  };
}

Map<String, dynamic> _assistanceSessionJson() {
  return {
    'assistance_session_id': 'tua_sess_1',
    'request_id': 'tua_req_1',
    'node_id': 'node_test',
    'agent_id': 'agent_mock',
    'session_id': 'sess_mock',
    'state': 'active',
    'created_by_device_id': 'dev_test',
    'created_at': '2026-06-05T12:00:00Z',
    'updated_at': '2026-06-05T12:00:01Z',
    'messages': [],
  };
}

Map<String, dynamic> _browserSessionJson() {
  return {
    'browser_session_id': 'br_1',
    'node_id': 'node_test',
    'agent_id': 'agent_mock',
    'session_id': 'sess_mock',
    'reason': 'Review browser state.',
    'state': 'active',
    'context_redacted': {},
    'user_action_notes': ['Reviewed.'],
    'created_at': '2026-06-05T12:00:00Z',
    'updated_at': '2026-06-05T12:00:01Z',
  };
}

Map<String, dynamic> _voiceSessionJson() {
  return {
    'voice_session_id': 'voice_1',
    'node_id': 'node_test',
    'agent_id': 'agent_mock',
    'session_id': 'sess_mock',
    'created_by_device_id': 'dev_test',
    'mode': 'text_fallback',
    'state': 'active',
    'created_at': '2026-06-05T12:00:00Z',
    'messages': [],
  };
}

Map<String, dynamic> _voiceMessageJson() {
  return {
    'voice_message_id': 'vm_1',
    'voice_session_id': 'voice_1',
    'sender_type': 'user',
    'body': 'Pause if risk increases.',
    'input_mode': 'text_fallback',
    'created_at': '2026-06-05T12:00:01Z',
  };
}
