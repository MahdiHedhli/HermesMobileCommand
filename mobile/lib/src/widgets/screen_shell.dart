import 'package:flutter/material.dart';

import '../routes.dart';

class ScreenShell extends StatelessWidget {
  const ScreenShell({
    required this.title,
    required this.selectedRoute,
    required this.body,
    super.key,
  });

  final String title;
  final String selectedRoute;
  final Widget body;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: body,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          final route = _routes[index];
          if (route != selectedRoute) {
            Navigator.of(context).pushReplacementNamed(route);
          }
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.hub_outlined), label: 'Agents'),
          NavigationDestination(icon: Icon(Icons.verified_user_outlined), label: 'Approvals'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
        ],
      ),
    );
  }

  int get _selectedIndex {
    final index = _routes.indexOf(selectedRoute);
    return index < 0 ? 0 : index;
  }

  static const _routes = [
    HermesRoutes.dashboard,
    HermesRoutes.agents,
    HermesRoutes.approvals,
    HermesRoutes.settings,
  ];
}

class StatusTile extends StatelessWidget {
  const StatusTile({
    required this.title,
    required this.value,
    required this.detail,
    super.key,
  });

  final String title;
  final String value;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(title),
      subtitle: Text(detail),
      trailing: Text(
        value,
        style: Theme.of(context).textTheme.titleLarge,
      ),
    );
  }
}
