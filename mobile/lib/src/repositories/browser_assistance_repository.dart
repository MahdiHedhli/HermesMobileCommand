import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class BrowserAssistanceRepository {
  const BrowserAssistanceRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<BrowserAssistanceSessionModel>> listSessions({
    String? state,
  }) async {
    final response = await apiClient.getJson(
      '/browser-assistance/sessions',
      query: {'state': state},
    );
    return (response['sessions'] as List<dynamic>? ?? const [])
        .map((item) => BrowserAssistanceSessionModel.fromJson(
            Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<BrowserAssistanceSessionModel> getSession(String sessionId) async {
    final response =
        await apiClient.getJson('/browser-assistance/sessions/$sessionId');
    return BrowserAssistanceSessionModel.fromJson(response);
  }

  Future<BrowserAssistanceSessionModel> recordEvent(
    String sessionId, {
    required String note,
  }) async {
    final response = await apiClient.postJson(
      '/browser-assistance/sessions/$sessionId/event',
      body: {'note': note},
    );
    return BrowserAssistanceSessionModel.fromJson(response);
  }

  Future<BrowserAssistanceSessionModel> returnControl(
    String sessionId, {
    required String summary,
  }) async {
    final response = await apiClient.postJson(
      '/browser-assistance/sessions/$sessionId/return-control',
      body: {'summary': summary},
    );
    return BrowserAssistanceSessionModel.fromJson(response);
  }
}
