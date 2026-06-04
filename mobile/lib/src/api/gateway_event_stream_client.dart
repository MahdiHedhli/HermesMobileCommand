import '../models/core_models.dart';
import '../security/secure_key_store.dart';

class GatewayEventStreamClient {
  const GatewayEventStreamClient({
    required this.gatewayBaseUrl,
    required this.keyStore,
  });

  final Uri gatewayBaseUrl;
  final SecureKeyStore keyStore;

  Stream<GatewayEvent> connect({String? after}) {
    return const Stream.empty();
  }
}
