import 'package:agentic_control_tower/src/clearance/canonical_json.dart';
import 'package:flutter_test/flutter_test.dart';

/// Build a `\uXXXX` escape from char codes (avoids embedding literal escapes).
final _backslash = String.fromCharCode(0x5c);
String _u(int unit) => '${_backslash}u${unit.toRadixString(16).padLeft(4, '0')}';

void main() {
  group('canonicalJson matches the gateway json.dumps encoder', () {
    test('empty object', () {
      expect(canonicalJson(<String, dynamic>{}), '{}');
    });

    test('sorts object keys by code unit and uses compact separators', () {
      expect(canonicalJson({'b': 1, 'a': 2, 'c': 3}), '{"a":2,"b":1,"c":3}');
    });

    test('nested objects are recursively sorted', () {
      expect(
        canonicalJson({
          'z': {'y': 1, 'x': 2},
          'a': [3, 2, 1],
        }),
        '{"a":[3,2,1],"z":{"x":2,"y":1}}',
      );
    });

    test('null, bool and int render like Python', () {
      expect(
        canonicalJson({'n': null, 't': true, 'f': false, 'i': 7}),
        '{"f":false,"i":7,"n":null,"t":true}',
      );
    });

    test('ensure_ascii escapes non-ASCII as lowercase uXXXX', () {
      // U+00E9 must be escaped (CPython json.dumps default ensure_ascii=True).
      final input = {'k': String.fromCharCode(0xE9)};
      expect(canonicalJson(input), '{"k":"${_u(0xe9)}"}');
    });

    test('astral chars emit two surrogate escapes like CPython', () {
      // U+1F600 -> surrogate pair D83D DE00.
      final input = String.fromCharCode(0xD83D) + String.fromCharCode(0xDE00);
      expect(canonicalJson(input), '"${_u(0xd83d)}${_u(0xde00)}"');
    });

    test('control characters use short escapes', () {
      expect(canonicalJson('a\nb\tc'), r'"a\nb\tc"');
    });

    test('DEL (0x7F) is escaped (CPython escapes code units >= 0x7F)', () {
      expect(canonicalJson(String.fromCharCode(0x7f)), '"${_u(0x7f)}"');
    });

    test('quote and backslash are escaped', () {
      expect(canonicalJson('a"b\\c'), r'"a\"b\\c"');
    });

    test('integral doubles keep a trailing .0 like Python floats', () {
      expect(canonicalJson(1.0), '1.0');
      expect(canonicalJson(0.5), '0.5');
    });
  });
}
