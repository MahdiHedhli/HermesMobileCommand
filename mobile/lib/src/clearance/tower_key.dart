import 'dart:convert';

import 'package:crypto/crypto.dart' as crypto;
import 'package:cryptography/cryptography.dart';

/// Derive the tower's Ed25519 proof public key from the node fingerprint, exactly
/// as the gateway does (`clearance_contract.py:_tower_private_key`):
///
///   seed = sha256("act-tower-proof:{node_fingerprint}")   // 32 bytes
///   key  = Ed25519 private key from that seed
///
/// The app pins the returned raw 32-byte public key at pairing (trust-on-first-use)
/// per tower and uses it to verify `ACT-CLEARANCE-PROOF-V1` signatures. There is no
/// tower-key distribution endpoint; deriving it from the pairing session's
/// node_fingerprint is the documented bootstrap.
Future<List<int>> deriveTowerPublicKey(String nodeFingerprint) async {
  final seed =
      crypto.sha256.convert(utf8.encode('act-tower-proof:$nodeFingerprint')).bytes;
  final keyPair = await Ed25519().newKeyPairFromSeed(seed);
  final publicKey = await keyPair.extractPublicKey();
  return publicKey.bytes;
}
