import 'dart:convert';

import 'package:crypto/crypto.dart' as crypto;
import 'package:cryptography/cryptography.dart';

import 'canonical_json.dart';

/// Verifier for ACT's published `ACT-CLEARANCE-PROOF-V1` clearance proof.
///
/// Mirrors `gateway/src/hermes_gateway/clearance_contract.py` byte-for-byte and
/// FAILS CLOSED: a clearance is only treated as granted when the tower's Ed25519
/// signature over the canonical proof string verifies against the pinned tower
/// public key AND the bound fields match what the operator's device expects.
///
/// The tower signs (and the app must NOT alter) the canonical string: nine lines
/// joined by a single "\n" with no trailing newline, in this exact order:
///   ACT-CLEARANCE-PROOF-V1, approval_id, params_fingerprint, short_code,
///   risk_family, expires_at, tower_id, contract_version, extensions_digest.
const proofCanonicalization = 'ACT-CLEARANCE-PROOF-V1';
const proofAlgorithm = 'Ed25519';

const proofBoundFields = <String>[
  'approval_id',
  'params_fingerprint',
  'short_code',
  'risk_family',
  'expires_at',
  'tower_id',
  'contract_version',
  'extensions_digest',
];

/// Outcome of a proof check. [verified] is the only thing the UI may treat as
/// "granted"; [reason] is a stable machine code for display/audit.
class ProofVerification {
  const ProofVerification(this.verified, this.reason);

  final bool verified;
  final String reason;

  static const ok = ProofVerification(true, 'verified');

  factory ProofVerification.fail(String reason) =>
      ProofVerification(false, reason);

  @override
  String toString() => 'ProofVerification(verified: $verified, reason: $reason)';
}

class ClearanceProofVerifier {
  const ClearanceProofVerifier();

  /// Rebuild the exact canonical proof string from the bound `material` fields.
  String canonicalProofString(Map<String, dynamic> material) {
    return [
      proofCanonicalization,
      _field(material, 'approval_id'),
      _field(material, 'params_fingerprint'),
      _field(material, 'short_code'),
      _field(material, 'risk_family'),
      _field(material, 'expires_at'),
      _field(material, 'tower_id'),
      _field(material, 'contract_version'),
      _field(material, 'extensions_digest'),
    ].join('\n');
  }

  /// Core fail-closed crypto check: const algorithm/canonicalization plus an
  /// Ed25519 verification of the base64url (no-pad) signature over the canonical
  /// string, using the trusted [towerPublicKey] (raw 32-byte Ed25519 key).
  Future<ProofVerification> verifySignature({
    required Map<String, dynamic> material,
    required Map<String, dynamic> proof,
    required List<int> towerPublicKey,
  }) async {
    if (proof['algorithm'] != proofAlgorithm) {
      return ProofVerification.fail('unexpected_algorithm');
    }
    if (proof['canonicalization'] != proofCanonicalization) {
      return ProofVerification.fail('unexpected_canonicalization');
    }
    final signatureValue = proof['signature'];
    if (signatureValue is! String || signatureValue.isEmpty) {
      return ProofVerification.fail('missing_signature');
    }
    final List<int> signatureBytes;
    try {
      signatureBytes = base64UrlDecodeNoPadding(signatureValue);
    } on Object {
      return ProofVerification.fail('bad_signature_encoding');
    }
    final message = utf8.encode(canonicalProofString(material));
    final algorithm = Ed25519();
    final bool valid;
    try {
      valid = await algorithm.verify(
        message,
        signature: Signature(
          signatureBytes,
          publicKey:
              SimplePublicKey(towerPublicKey, type: KeyPairType.ed25519),
        ),
      );
    } on Object {
      return ProofVerification.fail('invalid_signature');
    }
    return valid
        ? ProofVerification.ok
        : ProofVerification.fail('invalid_signature');
  }

  /// Full fail-closed verification for a live clearance object.
  ///
  /// In addition to the signature, this checks: the clearance has not expired,
  /// the short_code is the tower-derived value for (approval_id, params_fingerprint),
  /// and — when [expectedCapability] is supplied — that the (unsigned, v2-core)
  /// capability matches what the device requested out-of-band. Any failure
  /// returns a non-verified result; the UI must refuse to act on it.
  Future<ProofVerification> verifyClearance({
    required Map<String, dynamic> clearance,
    required List<int> towerPublicKey,
    String? expectedCapability,
    DateTime? now,
  }) async {
    final proof = clearance['proof'];
    if (proof is! Map) {
      return ProofVerification.fail('missing_proof');
    }
    final proofMap = Map<String, dynamic>.from(proof);
    final material = materialFromClearance(clearance);

    final signature = await verifySignature(
      material: material,
      proof: proofMap,
      towerPublicKey: towerPublicKey,
    );
    if (!signature.verified) {
      return signature;
    }

    final expiresAt = DateTime.tryParse(_field(material, 'expires_at'));
    if (expiresAt == null) {
      return ProofVerification.fail('bad_expires_at');
    }
    final reference = (now ?? DateTime.now()).toUtc();
    if (!expiresAt.toUtc().isAfter(reference)) {
      return ProofVerification.fail('expired');
    }

    final recomputedShortCode = computeShortCode(
      _field(material, 'approval_id'),
      _field(material, 'params_fingerprint'),
    );
    if (recomputedShortCode != _field(material, 'short_code')) {
      return ProofVerification.fail('short_code_mismatch');
    }

    if (expectedCapability != null &&
        clearance['capability'] != expectedCapability) {
      return ProofVerification.fail('capability_mismatch');
    }

    return ProofVerification.ok;
  }

  /// Project the proof "material" (bound fields) out of a canonical clearance
  /// object. ACT's `approval_id` is the canonical `request_id`; the proof's
  /// `extensions_digest` is authoritative for that bound field.
  Map<String, dynamic> materialFromClearance(Map<String, dynamic> clearance) {
    final proof = clearance['proof'];
    final proofMap = proof is Map ? Map<String, dynamic>.from(proof) : const {};
    return {
      'approval_id': clearance['approval_id'] ?? clearance['request_id'],
      'params_fingerprint': clearance['params_fingerprint'],
      'short_code': clearance['short_code'],
      'risk_family': clearance['risk_family'],
      'expires_at': clearance['expires_at'],
      'tower_id': clearance['tower_id'],
      'contract_version': clearance['contract_version'],
      'extensions_digest':
          proofMap['extensions_digest'] ?? clearance['extensions_digest'],
    };
  }

  /// short_code = first 10 hex chars of sha256("{approval_id}:{params_fingerprint}"),
  /// uppercased.
  String computeShortCode(String approvalId, String paramsFingerprint) {
    final digest =
        crypto.sha256.convert(utf8.encode('$approvalId:$paramsFingerprint'));
    return digest.toString().substring(0, 10).toUpperCase();
  }

  /// extensions_digest = sha256 hexdigest of canonical JSON of the extensions
  /// object alone (empty extensions => sha256 of "{}").
  String computeExtensionsDigest(Object? extensions) {
    return crypto.sha256
        .convert(utf8.encode(canonicalJson(extensions ?? <String, dynamic>{})))
        .toString();
  }

  /// params_fingerprint = sha256 hexdigest of canonical JSON of
  /// {"extensions": ..., "payload_redacted": ...}.
  String computeParamsFingerprint({
    Object? payloadRedacted,
    Object? extensions,
  }) {
    return crypto.sha256
        .convert(utf8.encode(canonicalJson({
          'extensions': extensions ?? <String, dynamic>{},
          'payload_redacted': payloadRedacted,
        })))
        .toString();
  }

  String _field(Map<String, dynamic> material, String key) {
    final value = material[key];
    return value == null ? '' : value.toString();
  }
}

/// base64url decode tolerating missing padding (matches the gateway).
List<int> base64UrlDecodeNoPadding(String value) {
  final padding = '=' * ((4 - value.length % 4) % 4);
  return base64Url.decode('$value$padding');
}
