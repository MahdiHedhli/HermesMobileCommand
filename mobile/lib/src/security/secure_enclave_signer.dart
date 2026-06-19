import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'device_request_signer.dart';
import 'secure_enclave_channel.dart';

/// [DeviceRequestSigner] backed by a Secure-Enclave (or honest software-dev)
/// P-256 key. The HMCP transport signature for every signed request is produced
/// by the enclave key behind a user-presence prompt, and the same key signs
/// clearance decisions and the pairing possession proof.
class SecureEnclaveDeviceRequestSigner implements DeviceRequestSigner {
  SecureEnclaveDeviceRequestSigner({
    required this.deviceId,
    required this.channel,
    required ClearanceKeyProtection protection,
    this.transportReuseSeconds = 60,
  }) : _protection = protection;

  final String deviceId;
  final SecureEnclaveChannel channel;
  final ClearanceKeyProtection _protection;

  /// Reuse window for routine signed requests (a screen-load burst should not
  /// re-prompt). Clearance decisions always use a fresh prompt via [signPayload].
  final double transportReuseSeconds;

  final Random _random = Random.secure();

  @override
  ClearanceKeyProtection get protection => _protection;

  @override
  Future<SignedRequestHeaders> sign({
    required String method,
    required String pathWithQuery,
    required Uint8List body,
  }) async {
    final timestamp =
        (DateTime.now().millisecondsSinceEpoch ~/ 1000).toString();
    final nonce = _newNonce();
    final canonical = canonicalRequest(
      method: method,
      pathWithQuery: pathWithQuery,
      timestamp: timestamp,
      nonce: nonce,
      body: body,
    );
    final signature = await channel.sign(
      data: Uint8List.fromList(utf8.encode(canonical)),
      reason: 'Authorize ${method.toUpperCase()} $pathWithQuery',
      allowReuseSeconds: transportReuseSeconds,
    );
    return SignedRequestHeaders({
      'X-HMCP-Device-Id': deviceId,
      'X-HMCP-Timestamp': timestamp,
      'X-HMCP-Nonce': nonce,
      'X-HMCP-Signature': signature,
      'X-HMCP-Key-Id': 'device:$deviceId',
    });
  }

  /// Sign an arbitrary payload (a clearance decision or the pairing possession
  /// proof). Uses the same reuse window as transport requests so a decision's
  /// per-decision signature and its HMCP transport signature share one
  /// user-presence prompt. Pass [fresh] to force a new prompt. Returns the
  /// base64url DER ECDSA-SHA256 signature.
  Future<String> signPayload(
    Uint8List data, {
    required String reason,
    bool fresh = false,
  }) {
    return channel.sign(
      data: data,
      reason: reason,
      allowReuseSeconds: fresh ? 0 : transportReuseSeconds,
    );
  }

  String _newNonce() {
    final bytes = List<int>.generate(16, (_) => _random.nextInt(256));
    return base64UrlNoPadding(bytes);
  }
}
