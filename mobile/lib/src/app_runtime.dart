import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api/gateway_api_client.dart';
import 'api/gateway_event_stream_client.dart';
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
  String _eventStreamStatus = 'Live stream idle';
  bool _eventStreamConnected = false;
  int _eventRevision = 0;
  String? _lastEventCursor;
  GatewayEvent? _lastEvent;
  final List<GatewayEvent> _recentEvents = [];
  StreamSubscription<GatewayEvent>? _eventSubscription;
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
  String get eventStreamStatus => _eventStreamStatus;
  bool get eventStreamConnected => _eventStreamConnected;
  int get eventRevision => _eventRevision;
  GatewayEvent? get lastEvent => _lastEvent;
  List<GatewayEvent> get recentEvents => List.unmodifiable(_recentEvents);
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
    if (isPaired && _accessToken != null) {
      await _startEventStream();
    }
    notifyListeners();
  }

  Future<void> saveGatewayBaseUrl(String value) async {
    _config = GatewayConfig.fromInput(value);
    await _configStore.save(_config);
    _connectionStatus = 'Gateway URL saved';
    if (isPaired && _accessToken != null) {
      await _restartEventStream();
    }
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
    await _restartEventStream();
    notifyListeners();
  }

  Future<void> clearPairing() async {
    await _stopEventStream();
    await _keyStore.clear();
    _deviceId = null;
    _accessToken = null;
    _refreshToken = null;
    _privateKey = null;
    _publicKey = null;
    _lastPairing = null;
    _connectionStatus = 'Pairing cleared';
    _eventStreamStatus = 'Live stream idle';
    _eventStreamConnected = false;
    _eventRevision += 1;
    _lastEventCursor = null;
    _lastEvent = null;
    _recentEvents.clear();
    notifyListeners();
  }

  Future<void> refreshLiveData() async {
    _eventRevision += 1;
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

  @override
  void dispose() {
    _eventSubscription?.cancel();
    super.dispose();
  }

  Future<void> _startEventStream() async {
    final token = _accessToken;
    if (token == null || token.isEmpty) {
      _eventStreamStatus = 'Pairing token unavailable';
      _eventStreamConnected = false;
      return;
    }
    await _eventSubscription?.cancel();
    _eventStreamStatus = 'Live stream connecting';
    _eventStreamConnected = false;
    _eventSubscription = GatewayEventStreamClient(
      config: _config,
      accessToken: token,
    ).connect(after: _lastEventCursor).listen(
      _handleGatewayEvent,
      onError: (Object error) {
        _eventStreamStatus = 'Live stream error: $error';
        _eventStreamConnected = false;
        notifyListeners();
      },
      onDone: () {
        _eventStreamStatus = 'Live stream disconnected';
        _eventStreamConnected = false;
        notifyListeners();
      },
    );
  }

  Future<void> _restartEventStream() async {
    await _stopEventStream();
    await _startEventStream();
  }

  Future<void> _stopEventStream() async {
    final subscription = _eventSubscription;
    _eventSubscription = null;
    await subscription?.cancel();
  }

  void _handleGatewayEvent(GatewayEvent event) {
    _lastEvent = event;
    _lastEventCursor = event.cursor;
    _recentEvents.insert(0, event);
    if (_recentEvents.length > 30) {
      _recentEvents.removeRange(30, _recentEvents.length);
    }
    _eventStreamConnected = true;
    _eventStreamStatus = 'Live: ${event.type}';
    _eventRevision += 1;
    notifyListeners();
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
