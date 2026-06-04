import 'package:flutter/material.dart';

import 'routes.dart';
import 'theme.dart';

class HermesMobileApp extends StatelessWidget {
  const HermesMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hermes Control',
      theme: hermesTheme(),
      initialRoute: HermesRoutes.dashboard,
      routes: HermesRoutes.routes,
      debugShowCheckedModeBanner: false,
    );
  }
}
