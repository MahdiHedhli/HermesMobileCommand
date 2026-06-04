import 'package:flutter/material.dart';

import '../repositories/alpha_repository.dart';
import '../routes.dart';
import '../widgets/alpha_components.dart';
import '../widgets/screen_shell.dart';

class VoiceScreen extends StatelessWidget {
  const VoiceScreen({
    required this.repository,
    super.key,
  });

  final AlphaRepository repository;

  @override
  Widget build(BuildContext context) {
    return ScreenShell(
      title: 'Voice',
      selectedRoute: HermesRoutes.voice,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          AlphaPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.mic_none_outlined, color: Theme.of(context).colorScheme.primary),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Voice Readiness',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                    const StatusPill(label: 'future', color: Color(0xFF5DADEC)),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'This alpha reserves the mobile voice surface without implementing streaming.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ),
          ),
          const SectionHeader(title: 'Planned Modes'),
          _VoiceModeRow(
            icon: Icons.radio_button_checked,
            title: 'Push To Talk',
            detail: 'MVP path for sending short operator instructions to Hermes voice mode.',
          ),
          _VoiceModeRow(
            icon: Icons.sync_alt_outlined,
            title: 'Half Duplex',
            detail: 'Walkie-talkie style turn taking for interventions during active missions.',
          ),
          _VoiceModeRow(
            icon: Icons.graphic_eq_outlined,
            title: 'Full Duplex',
            detail: 'Future WebRTC voice session with explicit approval confirmation phrases.',
          ),
          const SectionHeader(title: 'Safety Hooks'),
          AlphaPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                DetailRow(label: 'Approvals', value: 'Voice approval requires confirmation phrase.'),
                DetailRow(label: 'Audit', value: 'Every voice callback and decision is logged.'),
                DetailRow(label: 'Fallback', value: 'Text TUA remains available when audio is unavailable.'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _VoiceModeRow extends StatelessWidget {
  const _VoiceModeRow({
    required this.icon,
    required this.title,
    required this.detail,
  });

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AlphaPanel(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: Theme.of(context).colorScheme.secondary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(detail),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
