import 'package:flutter/material.dart';

import 'src/app_runtime.dart';
import 'src/app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final runtime = await HermesAppRuntime.create();
  runApp(HermesMobileApp(runtime: runtime));
}
