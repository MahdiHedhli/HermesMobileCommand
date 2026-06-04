import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class ApprovalsRepository {
  const ApprovalsRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<ApprovalRequestModel>> listPending() async {
    final response = await apiClient.getJson(
      '/approvals',
      query: {'state': 'pending'},
    );
    return _approvals(response);
  }

  Future<ApprovalRequestModel> getApproval(String approvalId) async {
    final response = await apiClient.getJson('/approvals/$approvalId');
    return ApprovalRequestModel.fromJson(response);
  }

  Future<ApprovalRequestModel> approveOnce(String approvalId) async {
    await apiClient.postJson('/approvals/$approvalId/approve_once');
    return getApproval(approvalId);
  }

  Future<ApprovalRequestModel> deny(String approvalId) async {
    await apiClient.postJson('/approvals/$approvalId/deny');
    return getApproval(approvalId);
  }
}

List<ApprovalRequestModel> _approvals(Map<String, dynamic> response) {
  return (response['approvals'] as List<dynamic>? ?? const [])
      .map((item) =>
          ApprovalRequestModel.fromJson(Map<String, dynamic>.from(item as Map)))
      .toList();
}
