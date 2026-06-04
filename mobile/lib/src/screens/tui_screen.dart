import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/alpha_models.dart';
import '../repositories/alpha_repository.dart';
import '../routes.dart';
import '../viewmodels/alpha_viewmodels.dart';
import '../widgets/alpha_components.dart';
import '../widgets/screen_shell.dart';

class TuiScreen extends StatefulWidget {
  const TuiScreen({
    required this.repository,
    super.key,
  });

  final AlphaRepository repository;

  @override
  State<TuiScreen> createState() => _TuiScreenState();
}

class _TuiScreenState extends State<TuiScreen> {
  late final TuiViewModel _viewModel;
  late Future<TerminalSessionAlpha> _session;
  TerminalKeyPage _page = TerminalKeyPage.controls;
  bool _loadedRoute = false;

  @override
  void initState() {
    super.initState();
    _viewModel = TuiViewModel(widget.repository);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loadedRoute) {
      return;
    }
    final sessionId = ModalRoute.of(context)?.settings.arguments as String? ??
        'terminal-release';
    _session = _viewModel.load(sessionId);
    _loadedRoute = true;
  }

  @override
  Widget build(BuildContext context) {
    return ScreenShell(
      title: 'TUI',
      selectedRoute: HermesRoutes.inbox,
      body: FutureBuilder<TerminalSessionAlpha>(
        future: _session,
        builder: (context, snapshot) {
          final session = snapshot.data;
          if (session == null) {
            return const Center(child: CircularProgressIndicator());
          }
          return Column(
            children: [
              _TerminalHeader(session: session),
              Expanded(child: _TerminalPane(session: session)),
              _KeyboardAccessory(
                page: _page,
                keys: _viewModel.keysForPage(_page),
                onPageSelected: (page) => setState(() => _page = page),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _TerminalHeader extends StatelessWidget {
  const _TerminalHeader({required this.session});

  final TerminalSessionAlpha session;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: AlphaPanel(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Icon(Icons.terminal_outlined,
                color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(session.agentName,
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 2),
                  Text('${session.node} - ${session.mission}'),
                ],
              ),
            ),
            IconButton(
              onPressed: () => _copyScrollback(context, session),
              icon: const Icon(Icons.copy_outlined),
              tooltip: 'Copy scrollback',
            ),
          ],
        ),
      ),
    );
  }
}

class _TerminalPane extends StatelessWidget {
  const _TerminalPane({required this.session});

  final TerminalSessionAlpha session;

  @override
  Widget build(BuildContext context) {
    final terminalStyle = Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: const Color(0xFFD8F8EA),
          fontFamily: 'monospace',
          height: 1.45,
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xFF080A0A),
          border:
              Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(8),
        ),
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            ...session.scrollback
                .map((line) => SelectableText(line, style: terminalStyle)),
            SelectableText('${session.prompt} ', style: terminalStyle),
          ],
        ),
      ),
    );
  }
}

class _KeyboardAccessory extends StatelessWidget {
  const _KeyboardAccessory({
    required this.page,
    required this.keys,
    required this.onPageSelected,
  });

  final TerminalKeyPage page;
  final List<String> keys;
  final ValueChanged<TerminalKeyPage> onPageSelected;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          border: Border(
              top: BorderSide(
                  color: Theme.of(context).colorScheme.outlineVariant)),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
          child: Column(
            children: [
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: TerminalKeyPage.values.map((candidate) {
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        selected: candidate == page,
                        label: Text(_pageLabel(candidate)),
                        onSelected: (_) => onPageSelected(candidate),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children:
                    keys.map((label) => _TerminalKey(label: label)).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TerminalKey extends StatelessWidget {
  const _TerminalKey({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 38,
      width: _keyWidth(label),
      child: OutlinedButton(
        onPressed: () {},
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.labelLarge,
        ),
      ),
    );
  }
}

Future<void> _copyScrollback(
    BuildContext context, TerminalSessionAlpha session) async {
  await Clipboard.setData(ClipboardData(text: session.scrollback.join('\n')));
  if (!context.mounted) {
    return;
  }
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Terminal scrollback copied')),
  );
}

String _pageLabel(TerminalKeyPage page) {
  return switch (page) {
    TerminalKeyPage.controls => 'Controls',
    TerminalKeyPage.symbols => 'Symbols',
    TerminalKeyPage.brackets => 'Brackets',
    TerminalKeyPage.functions => 'Functions',
  };
}

double _keyWidth(String label) {
  if (label.length >= 4) {
    return 72;
  }
  return 52;
}
