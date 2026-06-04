import 'package:flutter/material.dart';

import 'screens/agents_screen.dart';
import 'screens/approvals_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/settings_screen.dart';

class HermesRoutes {
  static const dashboard = '/';
  static const agents = '/agents';
  static const approvals = '/approvals';
  static const settings = '/settings';

  static Map<String, WidgetBuilder> get routes => {
        dashboard: (_) => const DashboardScreen(),
        agents: (_) => const AgentsScreen(),
        approvals: (_) => const ApprovalsScreen(),
        settings: (_) => const SettingsScreen(),
      };
}
