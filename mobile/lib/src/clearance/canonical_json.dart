/// Byte-exact reimplementation of the gateway's canonical JSON encoder.
///
/// Mirrors `gateway/src/hermes_gateway/security.py:canonical_json`:
///   json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
///
/// CPython's `json.dumps` defaults to `ensure_ascii=True`, so every code unit
/// >= 0x7F is escaped as `\uXXXX` (astral characters are emitted as the two
/// UTF-16 surrogate escapes, matching CPython). Keys are sorted by code unit.
///
/// This MUST match the gateway byte-for-byte: the app recomputes
/// `params_fingerprint` and `extensions_digest` over this output to verify a
/// clearance proof fail-closed, so any drift would reject VALID proofs.
library;

/// Encode [value] exactly as the gateway's `canonical_json` would.
String canonicalJson(Object? value) {
  final out = StringBuffer();
  _writeValue(out, value);
  return out.toString();
}

void _writeValue(StringBuffer out, Object? value) {
  if (value == null) {
    out.write('null');
  } else if (value is bool) {
    out.write(value ? 'true' : 'false');
  } else if (value is int) {
    out.write(value.toString());
  } else if (value is double) {
    out.write(_formatDouble(value));
  } else if (value is String) {
    _writeString(out, value);
  } else if (value is Map) {
    _writeMap(out, value);
  } else if (value is Iterable) {
    _writeList(out, value);
  } else {
    // CPython `default=str` fallback for otherwise non-serializable values.
    _writeString(out, value.toString());
  }
}

void _writeMap(StringBuffer out, Map<dynamic, dynamic> map) {
  final keys = map.keys.map((k) => k.toString()).toList()..sort();
  out.write('{');
  var first = true;
  for (final key in keys) {
    if (!first) out.write(',');
    first = false;
    _writeString(out, key);
    out.write(':');
    _writeValue(out, map[key]);
  }
  out.write('}');
}

void _writeList(StringBuffer out, Iterable<dynamic> list) {
  out.write('[');
  var first = true;
  for (final item in list) {
    if (!first) out.write(',');
    first = false;
    _writeValue(out, item);
  }
  out.write(']');
}

void _writeString(StringBuffer out, String value) {
  out.write('"');
  for (final unit in value.codeUnits) {
    switch (unit) {
      case 0x22: // "
        out.write(r'\"');
      case 0x5C: // backslash
        out.write(r'\\');
      case 0x08:
        out.write(r'\b');
      case 0x0C:
        out.write(r'\f');
      case 0x0A:
        out.write(r'\n');
      case 0x0D:
        out.write(r'\r');
      case 0x09:
        out.write(r'\t');
      default:
        // ensure_ascii: printable ASCII (0x20..0x7E) verbatim; everything else
        // (control chars < 0x20 and all code units >= 0x7F) as \uXXXX.
        if (unit < 0x20 || unit > 0x7E) {
          out.write('\\u');
          out.write(unit.toRadixString(16).padLeft(4, '0'));
        } else {
          out.writeCharCode(unit);
        }
    }
  }
  out.write('"');
}

/// Render a double the way CPython's `float.__repr__` would for the common
/// cases (integral values keep a trailing `.0`). Exotic floats (scientific
/// notation, NaN/Infinity which are not valid JSON anyway) are out of scope for
/// the redacted-payload shapes used by the clearance contract.
String _formatDouble(double value) {
  if (value == value.roundToDouble() && value.isFinite) {
    return '${value.toInt()}.0';
  }
  return value.toString();
}
