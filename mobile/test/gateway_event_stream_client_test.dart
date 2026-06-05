import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile_control_plane/src/api/gateway_event_stream_client.dart';
import 'package:hermes_mobile_control_plane/src/config/gateway_config.dart';

void main() {
  test('stream uri uses websocket scheme and access token', () {
    final client = GatewayEventStreamClient(
      config: GatewayConfig.fromInput('http://127.0.0.1:8787/v1'),
      accessToken: 'access-test',
    );

    final uri = client.streamUri(after: 'cursor-1');

    expect(uri.scheme, 'ws');
    expect(uri.path, '/v1/events/stream');
    expect(uri.queryParameters['access_token'], 'access-test');
    expect(uri.queryParameters['after'], 'cursor-1');
  });

  test('parses gateway event json string', () {
    final event = GatewayEventStreamClient.parseGatewayEvent(
      jsonEncode(_eventJson(cursor: 'evt_1', type: 'approval.requested')),
    );

    expect(event.cursor, 'evt_1');
    expect(event.type, 'approval.requested');
    expect(event.payload['approval_id'], 'appr_test');
  });

  test('reconnects using latest cursor', () async {
    final seenUris = <Uri>[];
    var connectCount = 0;
    final client = GatewayEventStreamClient(
      config: GatewayConfig.fromInput('http://127.0.0.1:8787/v1'),
      accessToken: 'access-test',
      initialBackoff: Duration.zero,
      maxReconnects: 1,
      socketConnector: (uri) {
        seenUris.add(uri);
        connectCount += 1;
        if (connectCount == 1) {
          return Stream<dynamic>.value(
            jsonEncode(_eventJson(cursor: 'cursor-1')),
          );
        }
        return Stream<dynamic>.value(
          jsonEncode(_eventJson(cursor: 'cursor-2')),
        );
      },
    );

    final events = await client.connect().take(2).toList();

    expect(events.map((event) => event.cursor), ['cursor-1', 'cursor-2']);
    expect(seenUris[1].queryParameters['after'], 'cursor-1');
  });
}

Map<String, dynamic> _eventJson({
  required String cursor,
  String type = 'system.health',
}) {
  return {
    'event_id': 'evt_$cursor',
    'cursor': cursor,
    'node_id': 'node_test',
    'type': type,
    'occurred_at': '2026-06-05T12:00:00Z',
    'payload': {'approval_id': 'appr_test'},
  };
}
