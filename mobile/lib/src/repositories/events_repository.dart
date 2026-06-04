import '../api/gateway_api_client.dart';
import '../models/core_models.dart';

class EventsRepository {
  const EventsRepository(this.apiClient);

  final GatewayApiClient apiClient;

  Future<List<GatewayEvent>> listRecent({String? after}) async {
    final response = await apiClient.getJson(
      '/events',
      query: {'after': after},
    );
    return (response['events'] as List<dynamic>? ?? const [])
        .map((item) =>
            GatewayEvent.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }
}
