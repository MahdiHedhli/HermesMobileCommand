import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class AgentsRepository {
  const AgentsRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<GatewayAgent>> listAgents({String? nodeId}) async {
    final response = await apiClient.getJson(
      '/agents',
      query: {'node_id': nodeId},
    );
    return (response['agents'] as List<dynamic>? ?? const [])
        .map((item) => GatewayAgent.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<GatewayAgent> getAgent({
    required String nodeId,
    required String agentId,
  }) async {
    final response = await apiClient.getJson(
      '/agents/$agentId',
      query: {'node_id': nodeId},
    );
    return GatewayAgent.fromJson(response);
  }
}
