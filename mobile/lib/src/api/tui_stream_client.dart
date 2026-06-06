import 'dart:async';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../config/gateway_config.dart';
import 'tui_protocol.dart';

typedef TuiSocketConnector = WebSocketChannel Function(Uri uri);

class TuiStreamClient {
  const TuiStreamClient({
    required this.config,
    TuiSocketConnector? socketConnector,
  }) : _socketConnector = socketConnector;

  final GatewayConfig config;
  final TuiSocketConnector? _socketConnector;

  Uri streamUri(String sessionId, {required String attachToken}) {
    final httpUri = config.resolve('/tui/sessions/$sessionId/stream', {
      'attach_token': attachToken,
    });
    final scheme = switch (httpUri.scheme) {
      'https' => 'wss',
      'http' => 'ws',
      _ => httpUri.scheme,
    };
    return httpUri.replace(scheme: scheme);
  }

  TuiStreamConnection connect(String sessionId, {required String attachToken}) {
    final connector = _socketConnector;
    final channel = connector == null
        ? WebSocketChannel.connect(
            streamUri(sessionId, attachToken: attachToken))
        : connector(streamUri(sessionId, attachToken: attachToken));
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
