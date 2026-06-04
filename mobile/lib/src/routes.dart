import 'package:flutter/material.dart';

import 'repositories/mock_alpha_repository.dart';
import 'screens/agent_detail_screen.dart';
import 'screens/agents_screen.dart';
import 'screens/approval_detail_screen.dart';
import 'screens/home_screen.dart';
import 'screens/inbox_screen.dart';
import 'screens/missions_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/tua_screen.dart';
import 'screens/tui_screen.dart';
import 'screens/voice_screen.dart';

class HermesRoutes {
  static const home = '/';
  static const dashboard = home;
  static const agents = '/agents';
  static const agentDetail = '/agents/detail';
  static const missions = '/missions';
  static const inbox = '/inbox';
  static const approvals = inbox;
  static const approvalDetail = '/approval';
  static const tua = '/tua';
  static const tui = '/tui';
  static const voice = '/voice';
  static const settings = '/settings';

  static const _repository = MockAlphaRepository();

  static Map<String, WidgetBuilder> get routes => {
        home: (_) => const HomeScreen(repository: _repository),
        agents: (_) => const AgentsScreen(repository: _repository),
        agentDetail: (_) => const AgentDetailScreen(repository: _repository),
        missions: (_) => const MissionsScreen(repository: _repository),
        inbox: (_) => const InboxScreen(repository: _repository),
        approvalDetail: (_) => const ApprovalDetailScreen(repository: _repository),
        tua: (_) => const TuaScreen(repository: _repository),
        tui: (_) => const TuiScreen(repository: _repository),
        voice: (_) => const VoiceScreen(repository: _repository),
        settings: (_) => const SettingsScreen(),
      };
}
