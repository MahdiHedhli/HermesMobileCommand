import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api/gateway_api_client.dart';
import 'config/gateway_config.dart';
import 'models/core_models.dart';
import 'repositories/agents_repository.dart';
import 'repositories/alpha_repository.dart';
import 'repositories/approvals_repository.dart';
import 'repositories/dashboard_repository.dart';
import 'repositories/gateway_alpha_repository.dart';
import 'repositories/mock_alpha_repository.dart';
import 'repositories/notifications_repository.dart';
import 'repositories/pairing_repository.dart';
import 'security/device_request_signer.dart';
import 'security/secure_key_store.dart';

class HermesAppRuntime extends ChangeNotifier {
  HermesAppRuntime({
    required GatewayConfigStore configStore,
    required SecureKeyStore keyStore,
  })  : _configStore = configStore,
        _keyStore = keyStore;

  final GatewayConfigStore _configStore;
  final SecureKeyStore _keyStore;
  final AlphaRepository _mockRepository = const MockAlphaRepository();

  GatewayConfig _config = GatewayConfig.loopback;
  String? _deviceId;
  String? _accessToken;
  String? _refreshToken;
  String? _privateKey;
  String? _publicKey;
  String _connectionStatus = 'Not checked';
  PairingSessionModel? _lastPairing;

  static Future<HermesAppRuntime> create() async {
    final preferences = await SharedPreferences.getInstance();
    final runtime = HermesAppRuntime(
      configStore: SharedPreferencesGatewayConfigStore(preferences),
      keyStore: SharedPreferencesSecureKeyStore(preferences),
    );
    await runtime.initialize();
    return runtime;
  }

  GatewayConfig get config => _config;
  String? get deviceId => _deviceId;
  String get connectionStatus => _connectionStatus;
  PairingSessionModel? get lastPairing => _lastPairing;
  bool get isPaired =>
      _deviceId != null && _privateKey != null && _publicKey != null;
  bool get hasAccessToken => _accessToken != null && _refreshToken != null;
  String get dataModeLabel => isPaired ? 'Gateway data' : 'Mock alpha data';

  AlphaRepository get alphaRepository {
    if (!isPaired) {
      return _mockRepository;
    }
    final apiClient = _signedApiClient();
    return GatewayAlphaRepository(
      dashboardRepository: DashboardRepository(apiClient),
      agentsRepository: AgentsRepository(apiClient),
      approvalsRepository: ApprovalsRepository(apiClient),
      notificationsRepository: NotificationsRepository(apiClient),
    );
  }

  Future<void> initialize() async {
    _config = await _configStore.read();
    _deviceId = await _keyStore.readDeviceId();
    _accessToken = await _keyStore.readAccessToken();
    _refreshToken = await _keyStore.readRefreshToken();
    _privateKey = await _keyStore.readDevicePrivateKey();
    _publicKey = await _keyStore.readDevicePublicKey();
    notifyListeners();
  }

  Future<void> saveGatewayBaseUrl(String value) async {
    _config = GatewayConfig.fromInput(value);
    await _configStore.save(_config);
    _connectionStatus = 'Gateway URL saved';
    notifyListeners();
  }

  Future<void> checkHealth() async {
    try {
      final response =
          await _unsignedApiClient().getJson('/health', signed: false);
      _connectionStatus =
          'Connected: ${response['node_id']} ${response['status']}';
    } on Object catch (error) {
      _connectionStatus = 'Connection failed: $error';
    }
    notifyListeners();
  }

  Future<PairingSessionModel> startPairing() async {
    final session = await PairingRepository(_unsignedApiClient()).startPairing(
      displayName: 'Hermes Mobile Alpha',
    );
    _lastPairing = session;
    _connectionStatus = 'Pairing started';
    notifyListeners();
    return session;
  }

  Future<void> completePairing(PairingSessionModel session) async {
    final keyPair = await DeviceKeyPair.generate();
    final completion =
        await PairingRepository(_unsignedApiClient()).completePairing(
      pairing: session,
      devicePublicKey: keyPair.publicKeyBase64,
    );
    await _keyStore.saveDeviceKeyPair(
      privateKey: keyPair.privateKeyBase64,
      publicKey: keyPair.publicKeyBase64,
    );
    await _keyStore.saveDeviceSession(
      deviceId: completion.deviceId,
      accessToken: completion.accessToken,
      refreshToken: completion.refreshToken,
    );
    _deviceId = completion.deviceId;
    _accessToken = completion.accessToken;
    _refreshToken = completion.refreshToken;
    _privateKey = keyPair.privateKeyBase64;
    _publicKey = keyPair.publicKeyBase64;
    _lastPairing = null;
    _connectionStatus = 'Paired with ${completion.node.displayName}';
    notifyListeners();
  }

  Future<void> clearPairing() async {
    await _keyStore.clear();
    _deviceId = null;
    _accessToken = null;
    _refreshToken = null;
    _privateKey = null;
    _publicKey = null;
    _lastPairing = null;
    _connectionStatus = 'Pairing cleared';
    notifyListeners();
  }

  GatewayApiClient _unsignedApiClient() {
    return GatewayApiClient(
      config: _config,
      signer: const UnavailableDeviceRequestSigner(),
    );
  }

  GatewayApiClient _signedApiClient() {
    final deviceId = _deviceId;
    final privateKey = _privateKey;
    final publicKey = _publicKey;
    if (deviceId == null || privateKey == null || publicKey == null) {
      return _unsignedApiClient();
    }
    return GatewayApiClient(
      config: _config,
      signer: Ed25519DeviceRequestSigner(
        deviceId: deviceId,
        keyPair: DeviceKeyPair.fromBase64(
          privateKey: privateKey,
          publicKey: publicKey,
        ),
      ),
    );
  }
}

class HermesRuntimeScope extends InheritedNotifier<HermesAppRuntime> {
  const HermesRuntimeScope({
    required HermesAppRuntime runtime,
    required super.child,
    super.key,
  }) : super(notifier: runtime);

  static HermesAppRuntime of(BuildContext context) {
    final scope =
        context.dependOnInheritedWidgetOfExactType<HermesRuntimeScope>();
    if (scope == null || scope.notifier == null) {
      throw StateError('Hermes runtime scope is not available.');
    }
    return scope.notifier!;
  }
}
