import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class MissionsRepository {
  const MissionsRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<MissionRecord>> listMissions({String? nodeId, String? agentId}) async {
    final response = await apiClient.getJson(
      '/missions',
      query: {'node_id': nodeId, 'agent_id': agentId},
    );
    return (response['missions'] as List<dynamic>? ?? const [])
        .map((item) => MissionRecord.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  Future<MissionRecord> getMission(String missionId) async {
    final response = await apiClient.getJson('/missions/$missionId');
    return MissionRecord.fromJson(response);
  }
}
