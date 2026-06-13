import 'package:flutter/material.dart';

import 'app_runtime.dart';
import 'routes.dart';
import 'theme.dart';

class HermesMobileApp extends StatelessWidget {
  const HermesMobileApp({
    required this.runtime,
    super.key,
  });

  final HermesAppRuntime runtime;

  @override
  Widget build(BuildContext context) {
    return HermesRuntimeScope(
      runtime: runtime,
      child: MaterialApp(
        title: 'Agentic Control Tower',
        theme: hermesTheme(),
        initialRoute: HermesRoutes.dashboard,
        routes: HermesRoutes.routes(runtime),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
