import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class ApprovalResponsesRepository {
  const ApprovalResponsesRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<ApprovalResponseModel> modified(
    String approvalId, {
    required String alternateDirective,
    List<Map<String, Object?>> constraints = const [],
  }) async {
    return _create(
      approvalId,
      body: {
        'decision_type': 'modified',
        'alternate_directive': alternateDirective,
        'constraints': constraints,
      },
    );
  }

  Future<ApprovalResponseModel> needsInfo(
    String approvalId, {
    required String userMessage,
  }) async {
    return _create(
      approvalId,
      body: {
        'decision_type': 'needs_info',
        'user_message': userMessage,
      },
    );
  }

  Future<ApprovalResponseModel> proposePolicy(
    String approvalId, {
    required String confirmationPhrase,
    List<Map<String, Object?>> constraints = const [],
  }) async {
    return _create(
      approvalId,
      body: {
        'decision_type': 'propose_policy',
        'confirmation_phrase': confirmationPhrase,
        'constraints': constraints,
      },
    );
  }

  Future<ApprovalResponseModel> _create(
    String approvalId, {
    required Map<String, Object?> body,
  }) async {
    final response = await apiClient.postJson(
      '/approvals/$approvalId/responses',
      body: body,
    );
    return ApprovalResponseModel.fromJson(response);
  }
}
