import 'package:flutter/material.dart';

import '../models/alpha_models.dart';
import '../repositories/alpha_repository.dart';
import '../routes.dart';
import '../viewmodels/alpha_viewmodels.dart';
import '../widgets/alpha_components.dart';
import '../widgets/screen_shell.dart';

class ApprovalDetailScreen extends StatelessWidget {
  const ApprovalDetailScreen({
    required this.repository,
    super.key,
  });

  final AlphaRepository repository;

  @override
  Widget build(BuildContext context) {
    final viewModel = ApprovalDetailViewModel(repository);
    final approvalId = ModalRoute.of(context)?.settings.arguments as String? ?? 'appr-shell';
    return ScreenShell(
      title: 'Approval',
      selectedRoute: HermesRoutes.inbox,
      body: FutureBuilder<ApprovalAlpha>(
        future: viewModel.load(approvalId),
        builder: (context, snapshot) {
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
                    Text(approval.summary, style: Theme.of(context).textTheme.bodyLarge),
                    const SizedBox(height: 14),
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
              _ApprovalActions(viewModel: viewModel, approval: approval),
            ],
          );
        },
      ),
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
              StatusPill(label: approval.risk, color: riskColor(context, approval.risk)),
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
  });

  final ApprovalDetailViewModel viewModel;
  final ApprovalAlpha approval;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: CommandButton(
                label: 'Approve',
                icon: Icons.verified_outlined,
                primary: true,
                onPressed: () => _showAction(context, 'Approve Once'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: CommandButton(
                label: 'Deny',
                icon: Icons.block_outlined,
                destructive: true,
                onPressed: () => _showAction(context, 'Deny'),
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
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
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
    _showAction(context, action);
  }

  void _showAction(BuildContext context, String action) {
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
