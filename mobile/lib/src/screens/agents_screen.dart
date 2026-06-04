import 'package:flutter/material.dart';

import '../routes.dart';
import '../widgets/screen_shell.dart';

class AgentsScreen extends StatelessWidget {
  const AgentsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const ScreenShell(
      title: 'Agents',
      selectedRoute: HermesRoutes.agents,
      body: Center(
        child: Text('Agent inventory placeholder'),
      ),
    );
  }
}
