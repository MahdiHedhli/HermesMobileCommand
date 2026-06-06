import 'package:flutter/material.dart';

import 'app_runtime.dart';
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

  static Map<String, WidgetBuilder> routes(HermesAppRuntime runtime) => {
        home: (_) =>
            HomeScreen(repository: runtime.alphaRepository, runtime: runtime),
        agents: (_) => AgentsScreen(repository: runtime.alphaRepository),
        agentDetail: (_) =>
            AgentDetailScreen(repository: runtime.alphaRepository),
        missions: (_) => MissionsScreen(repository: runtime.alphaRepository),
        inbox: (_) =>
            InboxScreen(repository: runtime.alphaRepository, runtime: runtime),
        approvalDetail: (_) => ApprovalDetailScreen(
            repository: runtime.alphaRepository, runtime: runtime),
        tua: (_) => TuaScreen(repository: runtime.alphaRepository),
        tui: (_) => TuiScreen(repository: runtime.alphaRepository, runtime: runtime),
        voice: (_) => VoiceScreen(repository: runtime.alphaRepository),
        settings: (_) => const SettingsScreen(),
      };
}
