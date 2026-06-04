import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class NotificationsRepository {
  const NotificationsRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<NotificationRecord>> listRecent({String? category}) async {
    final response = await apiClient.getJson(
      '/notifications',
      query: {'category': category},
    );
    return (response['notifications'] as List<dynamic>? ?? const [])
        .map((item) => NotificationRecord.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }
}
