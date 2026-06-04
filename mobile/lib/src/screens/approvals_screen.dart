import 'package:flutter/material.dart';

import '../routes.dart';
import '../widgets/screen_shell.dart';

class ApprovalsScreen extends StatelessWidget {
  const ApprovalsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const ScreenShell(
      title: 'Approvals',
      selectedRoute: HermesRoutes.approvals,
      body: Center(
        child: Text('Approval queue placeholder'),
      ),
    );
  }
}
