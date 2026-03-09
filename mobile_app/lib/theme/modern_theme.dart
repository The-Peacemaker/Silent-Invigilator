import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class ModernColors {
  // Core palette
  static const Color bgPrimary = Color(0xFF0A0A1A);
  static const Color bgSecondary = Color(0xFF0F0F2A);
  static const Color bgTertiary = Color(0xFF141432);

  // Accents
  static const Color accentCyan = Color(0xFF00D4FF);
  static const Color accentPurple = Color(0xFF7C3AED);

  // Status colors
  static const Color statusSafe = Color(0xFF10B981);
  static const Color statusWarn = Color(0xFFF59E0B);
  static const Color statusDanger = Color(0xFFEF4444);
  static const Color statusInfo = Color(0xFF3B82F6);

  // Text
  static const Color textPrimary = Color(0xFFE2E8F0);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF475569);

  // Glass/Borders
  static const Color glassBg = Color(0x0CFFFFFF); // ~5% white
  static const Color glassBorder = Color(0x14FFFFFF); // ~8% white
  static const Color borderSubtle = Color(0x0FFFFFFF); // ~6% white
}

class ModernTheme {
  static ThemeData get themeData {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: ModernColors.bgPrimary,
      primaryColor: ModernColors.accentCyan,

      // Typography
      textTheme: TextTheme(
        displayLarge: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
        displayMedium: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
        displaySmall: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
        headlineLarge: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        headlineMedium: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontWeight: FontWeight.w600,
        ),
        titleLarge: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontWeight: FontWeight.w600,
        ),

        bodyLarge: GoogleFonts.inter(color: ModernColors.textPrimary),
        bodyMedium: GoogleFonts.inter(color: ModernColors.textPrimary),
        bodySmall: GoogleFonts.inter(color: ModernColors.textSecondary),

        labelLarge: GoogleFonts.jetBrainsMono(color: ModernColors.textPrimary),
        labelMedium: GoogleFonts.jetBrainsMono(
          color: ModernColors.textSecondary,
        ),
      ),

      // App Bar
      appBarTheme: AppBarTheme(
        backgroundColor: ModernColors.bgPrimary.withOpacity(0.8),
        elevation: 0,
        centerTitle: true,
        iconTheme: const IconThemeData(color: ModernColors.textPrimary),
        titleTextStyle: GoogleFonts.outfit(
          color: ModernColors.textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),

      // Cards
      cardTheme: CardThemeData(
        color: ModernColors.glassBg,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: ModernColors.glassBorder, width: 1),
        ),
      ),
    );
  }

  // Premium glassmorphism decoration
  static BoxDecoration glassDecoration({
    double borderRadius = 16,
    bool active = false,
  }) {
    return BoxDecoration(
      color: active ? ModernColors.bgTertiary : ModernColors.glassBg,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: active
            ? ModernColors.accentCyan.withOpacity(0.3)
            : ModernColors.glassBorder,
        width: 1,
      ),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withOpacity(0.4),
          blurRadius: 32,
          offset: const Offset(0, 8),
        ),
      ],
    );
  }

  // Gradient Text Style helper
  static final Shader linearGradientShader = const LinearGradient(
    colors: <Color>[ModernColors.accentCyan, ModernColors.accentPurple],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  ).createShader(const Rect.fromLTWH(0.0, 0.0, 200.0, 70.0));

  // Custom button decoration
  static BoxDecoration primaryButtonDecoration() {
    return BoxDecoration(
      gradient: const LinearGradient(
        colors: [ModernColors.accentCyan, ModernColors.accentPurple],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      borderRadius: BorderRadius.circular(8),
      boxShadow: [
        BoxShadow(
          color: ModernColors.accentCyan.withOpacity(0.25),
          blurRadius: 20,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }
}
