import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class DashboardRepository {
  const DashboardRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<DashboardSnapshot> loadSnapshot() async {
    final inventory = await apiClient.getJson('/inventory');
    final agents = await apiClient.getJson('/agents');
    final approvals = await apiClient.getJson(
      '/approvals',
      query: {'state': 'pending'},
    );
    final notifications = await apiClient.getJson('/notifications');

    return DashboardSnapshot(
      nodes: _list(inventory['nodes']).map(GatewayNode.fromJson).toList(),
      agents: _list(agents['agents']).map(GatewayAgent.fromJson).toList(),
      pendingApprovals:
          _list(approvals['approvals']).map(ApprovalRequestModel.fromJson).toList(),
      notifications:
          _list(notifications['notifications']).map(NotificationRecord.fromJson).toList(),
    );
  }
}

List<Map<String, dynamic>> _list(Object? value) {
  return (value as List<dynamic>? ?? const [])
      .map((item) => Map<String, dynamic>.from(item as Map))
      .toList();
}
