import 'package:flutter/material.dart';

ThemeData hermesTheme() {
  const primary = Color(0xFF1B5E5A);
  const surface = Color(0xFFF7F8FA);

  return ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: primary,
      primary: primary,
      surface: surface,
    ),
    scaffoldBackgroundColor: surface,
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      elevation: 0,
      backgroundColor: surface,
      foregroundColor: Color(0xFF111827),
    ),
    listTileTheme: const ListTileThemeData(
      contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 4),
    ),
    useMaterial3: true,
  );
}
