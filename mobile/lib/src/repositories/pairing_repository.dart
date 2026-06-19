import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class PairingRepository {
  const PairingRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<PairingSessionModel> startPairing({
    required String displayName,
  }) async {
    final response = await apiClient.postJson(
      '/pairing/start',
      signed: false,
      body: {
        'display_name': displayName,
        // The operator initiates pairing from their own mobile surface and pins
        // the clearance channel to mobile_signed. The gateway still rejects any
        // device-side override of this at /pairing/complete (ACT-003.1.1).
        'clearance_channel': 'mobile_signed',
        'requested_permissions': [
          'read_state',
          'approve',
          'intervene',
          'tui',
          'browser_assist',
          'voice',
        ],
      },
    );
    return PairingSessionModel.fromJson(response);
  }

  Future<PairingCompletionModel> completePairing({
    required PairingSessionModel pairing,
    required String devicePublicKey,
    String? deviceKeyAlgorithm,
    String? devicePossessionProof,
  }) async {
    final response = await apiClient.postJson(
      '/pairing/complete',
      signed: false,
      body: {
        'pairing_id': pairing.pairingId,
        'challenge_response': pairing.pairingToken,
        'device_public_key': devicePublicKey,
        if (deviceKeyAlgorithm != null)
          'device_key_algorithm': deviceKeyAlgorithm,
        if (devicePossessionProof != null)
          'device_key_possession_proof': devicePossessionProof,
        'device': {
          'device_name': 'ACT Operator Alpha',
          'platform': 'ios',
          'app_instance_id': 'hmcp-mobile-alpha',
          'app_version': '0.2.0',
        },
      },
    );
    return PairingCompletionModel.fromJson(response);
  }
}
