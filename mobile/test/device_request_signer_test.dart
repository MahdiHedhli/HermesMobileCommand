import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:hermes_mobile_control_plane/src/security/device_request_signer.dart';

void main() {
  test('canonical request matches gateway format', () {
    final canonical = canonicalRequest(
      method: 'post',
      pathWithQuery: '/v1/approvals/appr_123/approve_once',
      timestamp: '1700000000',
      nonce: 'nonce-1',
      body: Uint8List.fromList(utf8.encode('{"x":1}')),
    );

    expect(
      canonical,
      [
        'HMCP-SIGN-V1',
        'POST',
        '/v1/approvals/appr_123/approve_once',
        '1700000000',
        'nonce-1',
        '5041bf1f713df204784353e82f6a4a535931cb64f1f4b4a5aeaffcb720918b22',
      ].join('\n'),
    );
  });

  test('ed25519 signer creates required HMCP headers', () async {
    final keyPair = await DeviceKeyPair.generate();
    final signer = Ed25519DeviceRequestSigner(
      deviceId: 'dev_test',
      keyPair: keyPair,
    );

    final headers = await signer.sign(
      method: 'GET',
      pathWithQuery: '/v1/approvals?state=pending',
      body: Uint8List(0),
    );

    expect(headers.values['X-HMCP-Device-Id'], 'dev_test');
    expect(headers.values['X-HMCP-Timestamp'], isNotEmpty);
    expect(headers.values['X-HMCP-Nonce'], isNotEmpty);
    expect(headers.values['X-HMCP-Signature'], isNotEmpty);
  });

  test('device key pair validates stored public/private match', () async {
    final keyPair = await DeviceKeyPair.generate();
    final restored = DeviceKeyPair.fromBase64(
      privateKey: keyPair.privateKeyBase64,
      publicKey: keyPair.publicKeyBase64,
    );

    expect(await restored.validatesPair(), isTrue);
  });
}
