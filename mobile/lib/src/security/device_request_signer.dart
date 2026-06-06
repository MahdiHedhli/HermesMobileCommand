import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:cryptography/cryptography.dart';

const hmcpSigningVersion = 'HMCP-SIGN-V1';

class SignedRequestHeaders {
  const SignedRequestHeaders(this.values);

  final Map<String, String> values;
}

abstract class DeviceRequestSigner {
  Future<SignedRequestHeaders> sign({
    required String method,
    required String pathWithQuery,
    required Uint8List body,
  });
}

class DeviceKeyPair {
  const DeviceKeyPair({
    required this.privateKeyBytes,
    required this.publicKeyBytes,
  });

  final List<int> privateKeyBytes;
  final List<int> publicKeyBytes;

  String get privateKeyBase64 => base64UrlNoPadding(privateKeyBytes);
  String get publicKeyBase64 => base64UrlNoPadding(publicKeyBytes);

  static Future<DeviceKeyPair> generate() async {
    final algorithm = Ed25519();
    final keyPair = await algorithm.newKeyPair();
    final privateKeyBytes = await keyPair.extractPrivateKeyBytes();
    final publicKey = await keyPair.extractPublicKey();
    return DeviceKeyPair(
      privateKeyBytes: privateKeyBytes,
      publicKeyBytes: publicKey.bytes,
    );
  }

  static DeviceKeyPair fromBase64({
    required String privateKey,
    required String publicKey,
  }) {
    return DeviceKeyPair(
      privateKeyBytes: base64UrlDecodeNoPadding(privateKey),
      publicKeyBytes: base64UrlDecodeNoPadding(publicKey),
    );
  }

  Future<bool> validatesPair() async {
    final algorithm = Ed25519();
    final signingKey = SimpleKeyPairData(
      privateKeyBytes,
      publicKey: SimplePublicKey(publicKeyBytes, type: KeyPairType.ed25519),
      type: KeyPairType.ed25519,
    );
    const probe = 'hmcp-device-key-validation';
    final signature = await algorithm.sign(utf8.encode(probe), keyPair: signingKey);
    return algorithm.verify(
      utf8.encode(probe),
      signature: Signature(
        signature.bytes,
        publicKey: SimplePublicKey(publicKeyBytes, type: KeyPairType.ed25519),
      ),
    );
  }
}

class Ed25519DeviceRequestSigner implements DeviceRequestSigner {
  Ed25519DeviceRequestSigner({
    required this.deviceId,
    required this.keyPair,
  });

  final String deviceId;
  final DeviceKeyPair keyPair;
  final _algorithm = Ed25519();
  final _random = Random.secure();

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
    final signingKey = SimpleKeyPairData(
      keyPair.privateKeyBytes,
      publicKey:
          SimplePublicKey(keyPair.publicKeyBytes, type: KeyPairType.ed25519),
      type: KeyPairType.ed25519,
    );
    final signature = await _algorithm.sign(
      utf8.encode(canonical),
      keyPair: signingKey,
    );
    return SignedRequestHeaders({
      'X-HMCP-Device-Id': deviceId,
      'X-HMCP-Timestamp': timestamp,
      'X-HMCP-Nonce': nonce,
      'X-HMCP-Signature': base64UrlNoPadding(signature.bytes),
    });
  }

  String _newNonce() {
    final bytes = List<int>.generate(16, (_) => _random.nextInt(256));
    return base64UrlNoPadding(bytes);
  }
}

class UnavailableDeviceRequestSigner implements DeviceRequestSigner {
  const UnavailableDeviceRequestSigner();

  @override
  Future<SignedRequestHeaders> sign({
    required String method,
    required String pathWithQuery,
    required Uint8List body,
  }) {
    throw StateError('Device request signer is not configured.');
  }
}

String canonicalRequest({
  required String method,
  required String pathWithQuery,
  required String timestamp,
  required String nonce,
  required Uint8List body,
}) {
  return [
    hmcpSigningVersion,
    method.toUpperCase(),
    pathWithQuery,
    timestamp,
    nonce,
    sha256.convert(body).toString(),
  ].join('\n');
}

String base64UrlNoPadding(List<int> bytes) {
  return base64UrlEncode(bytes).replaceAll('=', '');
}

List<int> base64UrlDecodeNoPadding(String value) {
  final padding = '=' * (-value.length % 4);
  return base64Url.decode('$value$padding');
}
