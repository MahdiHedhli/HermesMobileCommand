class PairingSessionModel {
  const PairingSessionModel({
    required this.pairingId,
    required this.challenge,
    required this.status,
    required this.nodeId,
    required this.nodeFingerprint,
    required this.expiresAt,
    this.pairingToken,
  });

  final String pairingId;
  final String? pairingToken;
  final String challenge;
  final String status;
  final String nodeId;
  final String nodeFingerprint;
  final DateTime expiresAt;

  factory PairingSessionModel.fromJson(Map<String, dynamic> json) {
    return PairingSessionModel(
      pairingId: json['pairing_id'] as String,
      pairingToken: json['pairing_token'] as String?,
      challenge: json['challenge'] as String,
      status: json['status'] as String,
      nodeId: json['node_id'] as String,
      nodeFingerprint: json['node_fingerprint'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String),
    );
  }
}

class PairingCompletionModel {
  const PairingCompletionModel({
    required this.node,
    required this.deviceId,
    required this.accessToken,
    required this.refreshToken,
  });

  final GatewayNode node;
  final String deviceId;
  final String accessToken;
  final String refreshToken;

  factory PairingCompletionModel.fromJson(Map<String, dynamic> json) {
    final device = Map<String, dynamic>.from(json['device'] as Map);
    final tokens = Map<String, dynamic>.from(json['tokens'] as Map);
    return PairingCompletionModel(
      node:
          GatewayNode.fromJson(Map<String, dynamic>.from(json['node'] as Map)),
      deviceId: device['device_id'] as String,
      accessToken: tokens['access_token'] as String,
      refreshToken: tokens['refresh_token'] as String,
    );
  }
}

class GatewayNode {
  const GatewayNode({
    required this.nodeId,
    required this.displayName,
    required this.environment,
    required this.health,
    this.tags = const [],
  });

  final String nodeId;
  final String displayName;
  final String environment;
  final String health;
  final List<String> tags;

  factory GatewayNode.fromJson(Map<String, dynamic> json) {
    return GatewayNode(
      nodeId: json['node_id'] as String,
      displayName: json['display_name'] as String,
      environment: json['environment'] as String,
      health: json['health'] as String,
      tags: _stringList(json['tags']),
    );
  }
}

class GatewayAgent {
  const GatewayAgent({
    required this.agentId,
    required this.nodeId,
    required this.displayName,
    required this.status,
    this.activeSessionId,
    this.currentTool,
    this.currentTarget,
  });

  final String agentId;
  final String nodeId;
  final String displayName;
  final String status;
  final String? activeSessionId;
  final String? currentTool;
  final String? currentTarget;

  factory GatewayAgent.fromJson(Map<String, dynamic> json) {
    return GatewayAgent(
      agentId: json['agent_id'] as String,
      nodeId: json['node_id'] as String,
      displayName: json['display_name'] as String,
      status: json['status'] as String,
      activeSessionId: json['active_session_id'] as String?,
      currentTool: json['current_tool'] as String?,
      currentTarget: json['current_target'] as String?,
    );
  }
}

class ApprovalRequestModel {
  const ApprovalRequestModel({
    required this.approvalId,
    required this.actionId,
    required this.nodeId,
    required this.agentId,
    required this.sessionId,
    required this.requestedTool,
    required this.riskLevel,
    required this.summary,
    required this.fullPayloadRedacted,
    required this.state,
    required this.expiresAt,
    required this.options,
    this.decisionScope,
  });

  final String approvalId;
  final String actionId;
  final String nodeId;
  final String agentId;
  final String sessionId;
  final String requestedTool;
  final String riskLevel;
  final String summary;
  final Map<String, dynamic> fullPayloadRedacted;
  final String state;
  final DateTime expiresAt;
  final List<String> options;
  final String? decisionScope;

  factory ApprovalRequestModel.fromJson(Map<String, dynamic> json) {
    return ApprovalRequestModel(
      approvalId: json['approval_id'] as String,
      actionId: json['action_id'] as String,
      nodeId: json['node_id'] as String,
      agentId: json['agent_id'] as String,
      sessionId: json['session_id'] as String,
      requestedTool: json['requested_tool'] as String,
      riskLevel: json['risk_level'] as String,
      summary: json['summary'] as String,
      fullPayloadRedacted:
          Map<String, dynamic>.from(json['full_payload_redacted'] as Map),
      state: json['state'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String),
      options: _stringList(json['options']),
      decisionScope: json['decision_scope'] as String?,
    );
  }
}

class NotificationRecord {
  const NotificationRecord({
    required this.notificationId,
    required this.category,
    required this.urgency,
    required this.state,
    required this.createdAt,
    this.title,
    this.body,
    this.agentId,
    this.sessionId,
  });

  final String notificationId;
  final String category;
  final String urgency;
  final String state;
  final DateTime createdAt;
  final String? title;
  final String? body;
  final String? agentId;
  final String? sessionId;

  factory NotificationRecord.fromJson(Map<String, dynamic> json) {
    return NotificationRecord(
      notificationId: json['notification_id'] as String,
      category: json['category'] as String,
      urgency: json['urgency'] as String,
      state: json['state'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      title: json['title_safe'] as String?,
      body: json['body_safe'] as String?,
      agentId: json['agent_id'] as String?,
      sessionId: json['session_id'] as String?,
    );
  }
}

class GatewayEvent {
  const GatewayEvent({
    required this.eventId,
    required this.cursor,
    required this.nodeId,
    required this.type,
    required this.occurredAt,
    required this.payload,
    this.agentId,
    this.sessionId,
  });

  final String eventId;
  final String cursor;
  final String nodeId;
  final String type;
  final DateTime occurredAt;
  final Map<String, dynamic> payload;
  final String? agentId;
  final String? sessionId;

  factory GatewayEvent.fromJson(Map<String, dynamic> json) {
    return GatewayEvent(
      eventId: json['event_id'] as String,
      cursor: json['cursor'] as String,
      nodeId: json['node_id'] as String,
      type: json['type'] as String,
      occurredAt: DateTime.parse(json['occurred_at'] as String),
      payload: Map<String, dynamic>.from(json['payload'] as Map),
      agentId: json['agent_id'] as String?,
      sessionId: json['session_id'] as String?,
    );
  }
}

class DashboardSnapshot {
  const DashboardSnapshot({
    required this.nodes,
    required this.agents,
    required this.pendingApprovals,
    required this.notifications,
  });

  final List<GatewayNode> nodes;
  final List<GatewayAgent> agents;
  final List<ApprovalRequestModel> pendingApprovals;
  final List<NotificationRecord> notifications;
}

List<String> _stringList(Object? value) {
  return (value as List<dynamic>? ?? const [])
      .map((item) => item as String)
      .toList();
}
