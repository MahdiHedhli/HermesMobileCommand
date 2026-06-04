import 'package:flutter/material.dart';

ThemeData hermesTheme() {
  const primary = Color(0xFF20D0A0);
  const secondary = Color(0xFFFFB84D);
  const tertiary = Color(0xFF5DADEC);
  const background = Color(0xFF101111);
  const surface = Color(0xFF191B1B);
  const surfaceBright = Color(0xFF222626);
  const text = Color(0xFFF4F7F5);
  const muted = Color(0xFF9EA7A3);

  return ThemeData(
    colorScheme: const ColorScheme.dark(
      primary: primary,
      secondary: secondary,
      tertiary: tertiary,
      surface: surface,
      surfaceContainerHighest: surfaceBright,
      onSurface: text,
      outline: muted,
      outlineVariant: Color(0xFF303636),
      error: Color(0xFFFF6B6B),
    ),
    scaffoldBackgroundColor: background,
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      elevation: 0,
      backgroundColor: background,
      foregroundColor: text,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: surface,
      indicatorColor: primary.withOpacity(0.16),
      labelTextStyle: WidgetStateProperty.resolveWith(
        (_) => const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    ),
    listTileTheme: const ListTileThemeData(
      contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 4),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surfaceBright,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide.none,
      ),
      hintStyle: const TextStyle(color: muted),
    ),
    useMaterial3: true,
  );
}
