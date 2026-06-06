import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile_control_plane/src/api/tui_protocol.dart';

void main() {
  test('encodes client input and paste frames', () {
    final input = jsonDecode(TuiClientFrame.input('ls\n').encode())
        as Map<String, dynamic>;
    final paste = jsonDecode(TuiClientFrame.paste('a\nb\n').encode())
        as Map<String, dynamic>;

    expect(input, {'type': 'input', 'data': 'ls\n'});
    expect(paste, {'type': 'paste', 'data': 'a\nb\n'});
  });

  test('parses server output frame', () {
    final frame = TuiServerFrame.parse(
      jsonEncode({
        'type': 'output',
        'session_id': 'tui_1',
        'data': 'hello\n',
      }),
    );

    expect(frame.type, 'output');
    expect(frame.sessionId, 'tui_1');
    expect(frame.data, 'hello\n');
  });

  test('maps mobile accessory keys to terminal sequences', () {
    expect(terminalSequenceForLabel('ESC'), '\x1b');
    expect(terminalSequenceForLabel('TAB'), '\t');
    expect(terminalSequenceForLabel('CTRL+C'), '\x03');
    expect(terminalSequenceForLabel('Left'), '\x1b[D');
    expect(terminalSequenceForLabel('/'), '/');
    expect(terminalSequenceForLabel('|'), '|');
    expect(terminalSequenceForLabel('~'), '~');
    expect(terminalSequenceForLabel('ALT'), isNull);
  });
}
