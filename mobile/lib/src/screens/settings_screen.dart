import 'package:flutter/material.dart';

import '../routes.dart';
import '../widgets/alpha_components.dart';
import '../widgets/screen_shell.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ScreenShell(
      title: 'Settings',
      selectedRoute: HermesRoutes.settings,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: const [
          AlphaPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StatusPill(label: 'Tailscale first', color: Color(0xFF20D0A0)),
                SizedBox(height: 14),
                Text('Gateway Profile'),
                SizedBox(height: 8),
                DetailRow(label: 'Base URL', value: 'http://100.x.y.z:8787'),
                DetailRow(label: 'Auth', value: 'Paired device signature'),
                DetailRow(label: 'Mode', value: 'Mock alpha data with gateway-ready repositories'),
              ],
            ),
          ),
          SectionHeader(title: 'Device Trust'),
          AlphaPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DetailRow(label: 'Device', value: 'iPhone operator alpha'),
                DetailRow(label: 'Key', value: 'Ed25519 signing abstraction reserved'),
                DetailRow(label: 'Storage', value: 'Secure key store abstraction pending platform binding'),
              ],
            ),
          ),
          SectionHeader(title: 'Safety Defaults'),
          AlphaPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DetailRow(label: 'Approvals', value: 'Fail closed'),
                DetailRow(label: 'Push', value: 'Notification records only in alpha'),
                DetailRow(label: 'Voice', value: 'Reserved; no streaming implementation'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
