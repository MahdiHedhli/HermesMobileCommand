import 'package:flutter/material.dart';

import '../routes.dart';
import '../widgets/screen_shell.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ScreenShell(
      title: 'Dashboard',
      selectedRoute: HermesRoutes.dashboard,
      body: ListView(
        children: const [
          StatusTile(
            title: 'Gateway',
            value: 'Not connected',
            detail: 'Pair a Hermes Control Gateway to begin.',
          ),
          StatusTile(
            title: 'Active agents',
            value: '0',
            detail: 'Live agent status will appear here.',
          ),
          StatusTile(
            title: 'Pending approvals',
            value: '0',
            detail: 'Risky actions requiring review will appear here.',
          ),
        ],
      ),
    );
  }
}
