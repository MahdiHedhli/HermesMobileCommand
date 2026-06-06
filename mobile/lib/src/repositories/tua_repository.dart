import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class TuaRepository {
  const TuaRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<AssistanceRequestModel>> listRequests({
    String? state,
  }) async {
    final response = await apiClient.getJson(
      '/tua/requests',
      query: {'state': state},
    );
    return (response['requests'] as List<dynamic>? ?? const [])
        .map((item) => AssistanceRequestModel.fromJson(
            Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<AssistanceRequestModel> getRequest(String requestId) async {
    final response = await apiClient.getJson('/tua/requests/$requestId');
    return AssistanceRequestModel.fromJson(response);
  }

  Future<AssistanceSessionModel> createSession(
    String requestId, {
    String? initialMessage,
  }) async {
    final response = await apiClient.postJson(
      '/tua/requests/$requestId/sessions',
      body: {'initial_message': initialMessage},
    );
    return AssistanceSessionModel.fromJson(response);
  }

  Future<AssistanceSessionModel> getSession(String sessionId) async {
    final response = await apiClient.getJson('/tua/sessions/$sessionId');
    return AssistanceSessionModel.fromJson(response);
  }

  Future<AssistanceMessageModel> sendMessage(
    String sessionId, {
    required String body,
  }) async {
    final response = await apiClient.postJson(
      '/tua/sessions/$sessionId/messages',
      body: {'body': body},
    );
    return AssistanceMessageModel.fromJson(response);
  }

  Future<AssistanceSessionModel> returnControl(
    String sessionId, {
    required String summary,
  }) async {
    final response = await apiClient.postJson(
      '/tua/sessions/$sessionId/return-control',
      body: {'summary': summary},
    );
    return AssistanceSessionModel.fromJson(response);
  }
}
