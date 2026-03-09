import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Design tokens matching the web app's CSS variables
class SketchColors {
  static const Color paper = Color(0xFFFAF7F0);
  static const Color paperDark = Color(0xFFF0EBE0);
  static const Color paperLine = Color(0xFFD9CFC0);
  static const Color ink = Color(0xFF1A1A2E);
  static const Color inkFaint = Color(0xFF4A4A6A);
  static const Color inkVeryFaint = Color(0xFF9A94B0);
  static const Color pencil = Color(0xFF5A5A7A);

  // Status colors — per SDD 7.1
  static const Color focused = Color(0xFF2D8A4E); // Green
  static const Color focusedBg = Color(0xFFE8F5ED);
  static const Color warn = Color(0xFFC8900A); // Yellow
  static const Color warnBg = Color(0xFFFEF9E6);
  static const Color alert = Color(0xFFB5600A); // Orange
  static const Color alertBg = Color(0xFFFEF0E6);
  static const Color danger = Color(0xFFC0392B); // Red
  static const Color dangerBg = Color(0xFFFDEAEA);
}

class SketchTheme {
  static TextStyle get sketchFont =>
      GoogleFonts.caveat(fontWeight: FontWeight.w700);

  static TextStyle get monoFont => GoogleFonts.specialElite();

  static TextStyle get bodyFont =>
      GoogleFonts.kalam(fontWeight: FontWeight.w400);

  static ThemeData get themeData => ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: SketchColors.paper,
    colorScheme: const ColorScheme(
      brightness: Brightness.light,
      primary: SketchColors.ink,
      onPrimary: SketchColors.paper,
      secondary: SketchColors.focused,
      onSecondary: Colors.white,
      error: SketchColors.danger,
      onError: Colors.white,
      surface: SketchColors.paper,
      onSurface: SketchColors.ink,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: SketchColors.ink,
      foregroundColor: SketchColors.paper,
      elevation: 0,
      titleTextStyle: GoogleFonts.caveat(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: SketchColors.paper,
      ),
    ),
    textTheme: TextTheme(
      displayLarge: GoogleFonts.caveat(
        fontSize: 48,
        fontWeight: FontWeight.w700,
        color: SketchColors.ink,
      ),
      displayMedium: GoogleFonts.caveat(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        color: SketchColors.ink,
      ),
      headlineMedium: GoogleFonts.caveat(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: SketchColors.ink,
      ),
      titleLarge: GoogleFonts.specialElite(
        fontSize: 16,
        color: SketchColors.ink,
      ),
      titleMedium: GoogleFonts.specialElite(
        fontSize: 14,
        color: SketchColors.pencil,
      ),
      bodyLarge: GoogleFonts.kalam(fontSize: 16, color: SketchColors.ink),
      bodyMedium: GoogleFonts.kalam(fontSize: 14, color: SketchColors.ink),
      labelSmall: GoogleFonts.specialElite(
        fontSize: 10,
        color: SketchColors.pencil,
        letterSpacing: 1.5,
      ),
    ),
  );
}
