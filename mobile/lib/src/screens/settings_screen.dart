import 'package:flutter/material.dart';

import '../routes.dart';
import '../widgets/screen_shell.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const ScreenShell(
      title: 'Settings',
      selectedRoute: HermesRoutes.settings,
      body: Center(
        child: Text('Pairing and gateway settings placeholder'),
      ),
    );
  }
}
