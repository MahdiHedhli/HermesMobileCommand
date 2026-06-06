import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class VoiceRepository {
  const VoiceRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<VoiceSessionModel> createSession({
    String agentId = 'agent_mock',
    String? sessionId,
    String mode = 'text_fallback',
  }) async {
    final response = await apiClient.postJson(
      '/voice/sessions',
      body: {
        'agent_id': agentId,
        'session_id': sessionId,
        'mode': mode,
      },
    );
    return VoiceSessionModel.fromJson(response);
  }

  Future<VoiceSessionModel> getSession(String sessionId) async {
    final response = await apiClient.getJson('/voice/sessions/$sessionId');
    return VoiceSessionModel.fromJson(response);
  }

  Future<VoiceMessageModel> sendMessage(
    String sessionId, {
    required String body,
    String inputMode = 'text_fallback',
  }) async {
    final response = await apiClient.postJson(
      '/voice/sessions/$sessionId/messages',
      body: {'body': body, 'input_mode': inputMode},
    );
    return VoiceMessageModel.fromJson(response);
  }

  Future<VoiceSessionModel> closeSession(String sessionId) async {
    final response = await apiClient.postJson('/voice/sessions/$sessionId/close');
    return VoiceSessionModel.fromJson(response);
  }
}
