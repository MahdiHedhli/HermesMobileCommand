import 'package:flutter/material.dart';

import '../models/alpha_models.dart';
import '../repositories/alpha_repository.dart';
import '../routes.dart';
import '../viewmodels/alpha_viewmodels.dart';
import '../widgets/alpha_components.dart';
import '../widgets/screen_shell.dart';

class ApprovalDetailScreen extends StatefulWidget {
  const ApprovalDetailScreen({
    required this.repository,
    super.key,
  });

  final AlphaRepository repository;

  @override
  State<ApprovalDetailScreen> createState() => _ApprovalDetailScreenState();
}

class _ApprovalDetailScreenState extends State<ApprovalDetailScreen> {
  late final ApprovalDetailViewModel _viewModel;
  late Future<ApprovalAlpha> _approval;
  String _approvalId = 'appr-shell';
  bool _busy = false;
  bool _loadedRoute = false;

  @override
  void initState() {
    super.initState();
    _viewModel = ApprovalDetailViewModel(widget.repository);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final argument = ModalRoute.of(context)?.settings.arguments;
    final approvalId = argument is String ? argument : 'appr-shell';
    if (!_loadedRoute || approvalId != _approvalId) {
      _approvalId = approvalId;
      _approval = _viewModel.load(_approvalId);
      _loadedRoute = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    return ScreenShell(
      title: 'Approval',
      selectedRoute: HermesRoutes.inbox,
      body: FutureBuilder<ApprovalAlpha>(
        future: _approval,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return _ApprovalError(error: snapshot.error.toString());
          }
          final approval = snapshot.data;
          if (approval == null) {
            return const Center(child: CircularProgressIndicator());
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            children: [
              _ApprovalHeader(approval: approval),
              const SectionHeader(title: 'Request Summary'),
              AlphaPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(approval.summary,
                        style: Theme.of(context).textTheme.bodyLarge),
                    const SizedBox(height: 14),
                    DetailRow(label: 'State', value: approval.state),
                    DetailRow(label: 'Tool', value: approval.requestedTool),
                    DetailRow(label: 'Agent', value: approval.agentName),
                    DetailRow(label: 'Node', value: approval.node),
                    DetailRow(label: 'Session', value: approval.session),
                    DetailRow(label: 'Expires', value: approval.expiresIn),
                  ],
                ),
              ),
              const SectionHeader(title: 'Redacted Payload'),
              AlphaPanel(
                child: SelectableText(
                  approval.payloadPreview,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontFamily: 'monospace',
                      ),
                ),
              ),
              const SectionHeader(title: 'Operator Constraints'),
              AlphaPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: approval.constraints
                      .map(
                        (constraint) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.check_circle_outline,
                                color: Theme.of(context).colorScheme.primary,
                                size: 18,
                              ),
                              const SizedBox(width: 8),
                              Expanded(child: Text(constraint)),
                            ],
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 22),
              _ApprovalActions(
                viewModel: _viewModel,
                approval: approval,
                busy: _busy,
                onDecision: _submitDecision,
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _submitDecision(
      String action, Future<ApprovalAlpha> Function() submit) async {
    setState(() => _busy = true);
    try {
      final updated = await submit();
      setState(() {
        _approval = Future.value(updated);
      });
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$action submitted')),
      );
    } on Object catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }
}

class _ApprovalError extends StatelessWidget {
  const _ApprovalError({required this.error});

  final String error;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        AlphaPanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              StatusPill(
                  label: 'gateway error',
                  color: Theme.of(context).colorScheme.error),
              const SizedBox(height: 12),
              Text(error),
              const SizedBox(height: 14),
              OutlinedButton.icon(
                onPressed: () =>
                    Navigator.of(context).pushNamed(HermesRoutes.settings),
                icon: const Icon(Icons.settings_outlined),
                label: const Text('Open Settings'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ApprovalHeader extends StatelessWidget {
  const _ApprovalHeader({required this.approval});

  final ApprovalAlpha approval;

  @override
  Widget build(BuildContext context) {
    return AlphaPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              StatusPill(
                  label: approval.risk,
                  color: riskColor(context, approval.risk)),
              const SizedBox(width: 8),
              StatusPill(
                  label: approval.state,
                  color: _stateColor(context, approval.state)),
              const Spacer(),
              Text(
                approval.expiresIn,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Theme.of(context).colorScheme.secondary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            approval.title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '${approval.agentName} wants permission to use ${approval.requestedTool}.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

class _ApprovalActions extends StatelessWidget {
  const _ApprovalActions({
    required this.viewModel,
    required this.approval,
    required this.busy,
    required this.onDecision,
  });

  final ApprovalDetailViewModel viewModel;
  final ApprovalAlpha approval;
  final bool busy;
  final Future<void> Function(
      String action, Future<ApprovalAlpha> Function() submit) onDecision;

  @override
  Widget build(BuildContext context) {
    final pending = approval.state == 'pending';
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: CommandButton(
                label: 'Approve',
                icon: Icons.verified_outlined,
                primary: true,
                onPressed: busy || !pending
                    ? () {}
                    : () => onDecision(
                          'Approve Once',
                          () => viewModel.approveOnce(approval.id),
                        ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: CommandButton(
                label: 'Deny',
                icon: Icons.block_outlined,
                destructive: true,
                onPressed: busy || !pending
                    ? () {}
                    : () => onDecision(
                          'Deny',
                          () => viewModel.deny(approval.id),
                        ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () => _showMore(context),
            icon: const Icon(Icons.more_horiz),
            label: const Text('More'),
          ),
        ),
      ],
    );
  }

  void _showMore(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
            children: [
              Text(
                'Decision Options',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              ...viewModel.moreActions.map(
                (action) => ListTile(
                  leading: Icon(_actionIcon(action)),
                  title: Text(action),
                  onTap: () {
                    Navigator.of(context).pop();
                    _handleMoreAction(context, action);
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _handleMoreAction(BuildContext context, String action) {
    if (action == 'Open TUA Session') {
      Navigator.of(context).pushNamed(HermesRoutes.tua, arguments: approval.id);
      return;
    }
    if (action == 'Open TUI Session') {
      Navigator.of(context).pushNamed(HermesRoutes.tui, arguments: approval.id);
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$action selected for ${approval.agentName}')),
    );
  }
}

IconData _actionIcon(String action) {
  if (action.startsWith('Approve')) {
    return Icons.verified_outlined;
  }
  return switch (action) {
    'Other' => Icons.edit_note_outlined,
    'More Info' => Icons.info_outline,
    'Open TUA Session' => Icons.support_agent_outlined,
    'Open TUI Session' => Icons.terminal_outlined,
    'Pause Agent' => Icons.pause_circle_outline,
    'Stop Task' => Icons.stop_circle_outlined,
    'Stop Agent' => Icons.power_settings_new,
    _ => Icons.block_outlined,
  };
}

Color _stateColor(BuildContext context, String state) {
  return switch (state) {
    'approved' => Theme.of(context).colorScheme.primary,
    'denied' => Theme.of(context).colorScheme.error,
    'expired' => Theme.of(context).colorScheme.outline,
    'cancelled' => Theme.of(context).colorScheme.outline,
    _ => Theme.of(context).colorScheme.secondary,
  };
}
