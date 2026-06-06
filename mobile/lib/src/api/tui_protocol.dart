import 'dart:convert';

class TuiClientFrame {
  const TuiClientFrame._(this.values);

  final Map<String, Object?> values;

  factory TuiClientFrame.input(String data) =>
      TuiClientFrame._({'type': 'input', 'data': data});

  factory TuiClientFrame.paste(String data) =>
      TuiClientFrame._({'type': 'paste', 'data': data});

  factory TuiClientFrame.resize({required int rows, required int cols}) =>
      TuiClientFrame._({'type': 'resize', 'rows': rows, 'cols': cols});

  factory TuiClientFrame.ping() => const TuiClientFrame._({'type': 'ping'});

  factory TuiClientFrame.detach() => const TuiClientFrame._({'type': 'detach'});

  factory TuiClientFrame.close() => const TuiClientFrame._({'type': 'close'});

  String encode() => jsonEncode(_withoutNullValues(values));
}

class TuiServerFrame {
  const TuiServerFrame({
    required this.type,
    required this.sessionId,
    this.data,
    this.state,
    this.message,
  });

  final String type;
  final String sessionId;
  final String? data;
  final String? state;
  final String? message;

  factory TuiServerFrame.fromJson(Map<String, dynamic> json) {
    return TuiServerFrame(
      type: json['type'] as String,
      sessionId: json['session_id'] as String? ?? '',
      data: json['data'] as String?,
      state: json['state'] as String?,
      message: json['message'] as String?,
    );
  }

  factory TuiServerFrame.parse(Object raw) {
    if (raw is String) {
      return TuiServerFrame.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    }
    if (raw is Map<String, dynamic>) {
      return TuiServerFrame.fromJson(raw);
    }
    if (raw is Map) {
      return TuiServerFrame.fromJson(Map<String, dynamic>.from(raw));
    }
    throw FormatException('Unsupported TUI frame payload: $raw');
  }
}

String? terminalSequenceForLabel(String label) {
  return switch (label) {
    'ESC' => '\x1b',
    'TAB' => '\t',
    'CTRL' || 'CTRL+C' => '\x03',
    'Left' => '\x1b[D',
    'Up' => '\x1b[A',
    'Down' => '\x1b[B',
    'Right' => '\x1b[C',
    'Home' => '\x1b[H',
    'End' => '\x1b[F',
    'PgUp' => '\x1b[5~',
    'PgDn' => '\x1b[6~',
    'F1' => '\x1bOP',
    'F2' => '\x1bOQ',
    'F3' => '\x1bOR',
    'F4' => '\x1bOS',
    'F5' => '\x1b[15~',
    'F6' => '\x1b[17~',
    'F7' => '\x1b[18~',
    'F8' => '\x1b[19~',
    'F9' => '\x1b[20~',
    'F10' => '\x1b[21~',
    'F11' => '\x1b[23~',
    'F12' => '\x1b[24~',
    '{}' => '{}',
    '[]' => '[]',
    '()' => '()',
    '<>' => '<>',
    'ALT' || 'CMD' => null,
    _ => label.length == 1 ? label : null,
  };
}

Map<String, Object?> _withoutNullValues(Map<String, Object?> body) {
  return {
    for (final entry in body.entries)
      if (entry.value != null) entry.key: entry.value,
  };
}
