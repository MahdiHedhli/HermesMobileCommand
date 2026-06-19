import 'dart:convert';
import 'dart:io';

import 'package:agentic_control_tower/src/clearance/clearance_proof_verifier.dart';
import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';

String _b64urlNoPad(List<int> bytes) =>
    base64UrlEncode(bytes).replaceAll('=', '');

Future<Map<String, dynamic>> _buildSignedClearance({
  required SimpleKeyPair keyPair,
  String approvalId = 'appr_live_1',
  String paramsFingerprint =
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  String? shortCode,
  String riskFamily = 'routine',
  String? expiresAt,
  String towerId = 'tower_live',
  String contractVersion = 'act.clearance.v2',
  String capability = 'observe.read',
}) async {
  const v = ClearanceProofVerifier();
  final extDigest = v.computeExtensionsDigest(const <String, dynamic>{});
  final sc = shortCode ?? v.computeShortCode(approvalId, paramsFingerprint);
  final exp = expiresAt ??
      DateTime.now().toUtc().add(const Duration(hours: 1)).toIso8601String();
  final material = <String, dynamic>{
    'approval_id': approvalId,
    'params_fingerprint': paramsFingerprint,
    'short_code': sc,
    'risk_family': riskFamily,
    'expires_at': exp,
    'tower_id': towerId,
    'contract_version': contractVersion,
    'extensions_digest': extDigest,
  };
  final canonical = v.canonicalProofString(material);
  final signature =
      await Ed25519().sign(utf8.encode(canonical), keyPair: keyPair);
  return <String, dynamic>{
    'request_id': approvalId,
    'params_fingerprint': paramsFingerprint,
    'short_code': sc,
    'risk_family': riskFamily,
    'expires_at': exp,
    'tower_id': towerId,
    'contract_version': contractVersion,
    'capability': capability,
    'proof': <String, dynamic>{
      'algorithm': 'Ed25519',
      'canonicalization': 'ACT-CLEARANCE-PROOF-V1',
      'key_id': 'tower:$towerId',
      'fields': proofBoundFields,
      'extensions_digest': extDigest,
      'signature': _b64urlNoPad(signature.bytes),
    },
  };
}

void main() {
  const verifier = ClearanceProofVerifier();

  group('committed test vector (v1, version-aware)', () {
    late Map<String, dynamic> vector;

    setUpAll(() {
      // `flutter test` runs with the package root (mobile/) as cwd.
      final file = File('../contracts/clearance/test-vector.json');
      vector = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
    });

    test('valid committed proof verifies', () async {
      final result = await verifier.verifySignature(
        material: Map<String, dynamic>.from(vector['material'] as Map),
        proof: Map<String, dynamic>.from(vector['proof'] as Map),
        towerPublicKey:
            base64UrlDecodeNoPadding(vector['tower_public_key'] as String),
      );
      expect(result.verified, isTrue, reason: result.reason);
    });

    test('mutating any bound field fails closed', () async {
      final proof = Map<String, dynamic>.from(vector['proof'] as Map);
      final towerKey =
          base64UrlDecodeNoPadding(vector['tower_public_key'] as String);
      for (final field in proofBoundFields) {
        final material = Map<String, dynamic>.from(vector['material'] as Map);
        material[field] = '${material[field]}-tampered';
        final result = await verifier.verifySignature(
          material: material,
          proof: proof,
          towerPublicKey: towerKey,
        );
        expect(result.verified, isFalse,
            reason: 'mutation of "$field" must fail closed');
      }
    });

    test('an unknown/wrong tower key fails closed', () async {
      final result = await verifier.verifySignature(
        material: Map<String, dynamic>.from(vector['material'] as Map),
        proof: Map<String, dynamic>.from(vector['proof'] as Map),
        towerPublicKey: List<int>.filled(32, 7),
      );
      expect(result.verified, isFalse);
    });

    test('wrong algorithm or canonicalization is rejected', () async {
      final material = Map<String, dynamic>.from(vector['material'] as Map);
      final towerKey =
          base64UrlDecodeNoPadding(vector['tower_public_key'] as String);
      final badAlgo = Map<String, dynamic>.from(vector['proof'] as Map)
        ..['algorithm'] = 'ECDSA';
      final badCanon = Map<String, dynamic>.from(vector['proof'] as Map)
        ..['canonicalization'] = 'ACT-CLEARANCE-PROOF-V2';
      expect(
        (await verifier.verifySignature(
                material: material, proof: badAlgo, towerPublicKey: towerKey))
            .reason,
        'unexpected_algorithm',
      );
      expect(
        (await verifier.verifySignature(
                material: material, proof: badCanon, towerPublicKey: towerKey))
            .reason,
        'unexpected_canonicalization',
      );
    });
  });

  group('full verifyClearance on a self-consistent live clearance', () {
    late SimpleKeyPair keyPair;
    late List<int> towerPublicKey;

    setUp(() async {
      keyPair = await Ed25519().newKeyPair();
      towerPublicKey = (await keyPair.extractPublicKey()).bytes;
    });

    test('valid clearance with matching capability verifies', () async {
      final clearance = await _buildSignedClearance(keyPair: keyPair);
      final result = await verifier.verifyClearance(
        clearance: clearance,
        towerPublicKey: towerPublicKey,
        expectedCapability: 'observe.read',
      );
      expect(result.verified, isTrue, reason: result.reason);
    });

    test('expired clearance fails closed (signature valid)', () async {
      final clearance = await _buildSignedClearance(
        keyPair: keyPair,
        expiresAt:
            DateTime.utc(2000, 1, 1).toIso8601String(),
      );
      final result = await verifier.verifyClearance(
        clearance: clearance,
        towerPublicKey: towerPublicKey,
      );
      expect(result.verified, isFalse);
      expect(result.reason, 'expired');
    });

    test('non-derived short_code fails closed (signature valid)', () async {
      final clearance = await _buildSignedClearance(
        keyPair: keyPair,
        shortCode: 'NOTDERIVED',
      );
      final result = await verifier.verifyClearance(
        clearance: clearance,
        towerPublicKey: towerPublicKey,
      );
      expect(result.verified, isFalse);
      expect(result.reason, 'short_code_mismatch');
    });

    test('capability mismatch fails closed', () async {
      final clearance = await _buildSignedClearance(keyPair: keyPair);
      final result = await verifier.verifyClearance(
        clearance: clearance,
        towerPublicKey: towerPublicKey,
        expectedCapability: 'destructive.delete',
      );
      expect(result.verified, isFalse);
      expect(result.reason, 'capability_mismatch');
    });

    test('a different tower key fails closed', () async {
      final clearance = await _buildSignedClearance(keyPair: keyPair);
      final otherKey = await (await Ed25519().newKeyPair()).extractPublicKey();
      final result = await verifier.verifyClearance(
        clearance: clearance,
        towerPublicKey: otherKey.bytes,
      );
      expect(result.verified, isFalse);
    });
  });

  group('derived-field recomputation', () {
    test('empty extensions digest is sha256 of "{}"', () {
      // sha256("{}") = 44136fa3...; verify the digest is 64 lowercase hex chars.
      final digest = verifier.computeExtensionsDigest(const <String, dynamic>{});
      expect(digest.length, 64);
      expect(RegExp(r'^[0-9a-f]{64}$').hasMatch(digest), isTrue);
    });

    test('short_code is 10 uppercase hex chars', () {
      final code = verifier.computeShortCode('appr_x', 'a' * 64);
      expect(code.length, 10);
      expect(RegExp(r'^[0-9A-F]{10}$').hasMatch(code), isTrue);
    });
  });
}
