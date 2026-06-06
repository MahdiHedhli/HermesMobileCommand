import 'dart:async';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../config/gateway_config.dart';
import 'tui_protocol.dart';

typedef TuiSocketConnector = WebSocketChannel Function(Uri uri);

class TuiStreamClient {
  const TuiStreamClient({
    required this.config,
    required this.accessToken,
    TuiSocketConnector? socketConnector,
  }) : _socketConnector = socketConnector;

  final GatewayConfig config;
  final String accessToken;
  final TuiSocketConnector? _socketConnector;

  Uri streamUri(String sessionId) {
    final httpUri = config.resolve('/tui/sessions/$sessionId/stream', {
      'access_token': accessToken,
    });
    final scheme = switch (httpUri.scheme) {
      'https' => 'wss',
      'http' => 'ws',
      _ => httpUri.scheme,
    };
    return httpUri.replace(scheme: scheme);
  }

  TuiStreamConnection connect(String sessionId) {
    final connector = _socketConnector;
    final channel = connector == null
        ? WebSocketChannel.connect(streamUri(sessionId))
        : connector(streamUri(sessionId));
    return TuiStreamConnection(channel);
  }
}

class TuiStreamConnection {
  TuiStreamConnection(this._channel);

  final WebSocketChannel _channel;

  Stream<TuiServerFrame> get frames =>
      _channel.stream.map((raw) => TuiServerFrame.parse(raw));

  void send(TuiClientFrame frame) {
    _channel.sink.add(frame.encode());
  }

  Future<void> close() => _channel.sink.close();
}
