import 'package:flutter/material.dart';

import '../models/alpha_models.dart';
import '../repositories/alpha_repository.dart';
import '../routes.dart';
import '../viewmodels/alpha_viewmodels.dart';
import '../widgets/alpha_components.dart';
import '../widgets/screen_shell.dart';

class TuaScreen extends StatefulWidget {
  const TuaScreen({
    required this.repository,
    super.key,
  });

  final AlphaRepository repository;

  @override
  State<TuaScreen> createState() => _TuaScreenState();
}

class _TuaScreenState extends State<TuaScreen> {
  late final TuaViewModel _viewModel;
  late Future<void> _load;
  final _replyController = TextEditingController();
  bool _loadedRoute = false;

  @override
  void initState() {
    super.initState();
    _viewModel = TuaViewModel(widget.repository);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loadedRoute) {
      return;
    }
    final sessionId = ModalRoute.of(context)?.settings.arguments as String? ?? 'assist-release';
    _load = _viewModel.load(sessionId);
    _loadedRoute = true;
  }

  @override
  void dispose() {
    _replyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScreenShell(
      title: 'TUA',
      selectedRoute: HermesRoutes.inbox,
      body: FutureBuilder<void>(
        future: _load,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          return AnimatedBuilder(
            animation: _viewModel,
            builder: (context, _) {
              final session = _viewModel.session;
              if (session == null) {
                return const Center(child: Text('Assistance session unavailable'));
              }
              return Column(
                children: [
                  _SessionHeader(session: session, returnedToAgent: _viewModel.returnedToAgent),
                  Expanded(
                    child: ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                      itemCount: _viewModel.messages.length,
                      itemBuilder: (context, index) {
                        return _MessageBubble(message: _viewModel.messages[index]);
                      },
                    ),
                  ),
                  _ReplyBar(
                    controller: _replyController,
                    onSend: () {
                      _viewModel.sendReply(_replyController.text);
                      _replyController.clear();
                    },
                    onReturn: _viewModel.returnToAgent,
                  ),
                ],
              );
            },
          );
        },
      ),
    );
  }
}

class _SessionHeader extends StatelessWidget {
  const _SessionHeader({
    required this.session,
    required this.returnedToAgent,
  });

  final AssistanceSessionAlpha session;
  final bool returnedToAgent;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
      child: AlphaPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusPill(
                  label: returnedToAgent ? 'returned' : _stateLabel(session.state),
                  color: returnedToAgent
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.secondary,
                ),
                const Spacer(),
                Text(session.node, style: Theme.of(context).textTheme.labelMedium),
              ],
            ),
            const SizedBox(height: 12),
            Text(session.agentName, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(session.mission),
            const SizedBox(height: 10),
            Text(session.reason, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final AssistanceMessageAlpha message;

  @override
  Widget build(BuildContext context) {
    final bubbleColor = message.fromUser
        ? Theme.of(context).colorScheme.primary.withOpacity(0.18)
        : Theme.of(context).colorScheme.surface;
    final borderColor = message.fromUser
        ? Theme.of(context).colorScheme.primary.withOpacity(0.55)
        : Theme.of(context).colorScheme.outlineVariant;
    return Align(
      alignment: message.fromUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 320),
        child: Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: bubbleColor,
              border: Border.all(color: borderColor),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment:
                    message.fromUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                children: [
                  Text(
                    '${message.sender} - ${message.timeLabel}',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(message.body),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ReplyBar extends StatelessWidget {
  const _ReplyBar({
    required this.controller,
    required this.onSend,
    required this.onReturn,
  });

  final TextEditingController controller;
  final VoidCallback onSend;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          border: Border(top: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller,
                      minLines: 1,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        hintText: 'Send operator instruction',
                        prefixIcon: Icon(Icons.edit_note_outlined),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: onSend,
                    icon: const Icon(Icons.send_outlined),
                    tooltip: 'Send',
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: onReturn,
                  icon: const Icon(Icons.keyboard_return_outlined),
                  label: const Text('Return To Agent'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _stateLabel(AssistanceState state) {
  return switch (state) {
    AssistanceState.requested => 'requested',
    AssistanceState.active => 'active',
    AssistanceState.waitingOnUser => 'waiting',
    AssistanceState.userControlling => 'controlling',
    AssistanceState.returnedToAgent => 'returned',
    AssistanceState.closed => 'closed',
  };
}
