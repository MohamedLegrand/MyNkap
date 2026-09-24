import 'package:flutter/material.dart';

import 'app_colors.dart';

/// Thèmes clair/sombre de l'app — voir [AppColors] pour la palette. Le
/// choix clair/sombre/système reste au niveau OS (`ThemeMode.system` posé
/// dans `app.dart`) : pas de bascule manuelle dans l'app pour l'instant,
/// contrairement au web (voir hooks/useDarkMode côté frontend) — à ajouter
/// plus tard si besoin, sans impact sur cette structure.
class AppTheme {
  AppTheme._();

  static ThemeData get light => _build(
        brightness: Brightness.light,
        background: AppColors.lightBackground,
        foreground: AppColors.lightForeground,
        primary: AppColors.lightPrimary,
        card: AppColors.lightCard,
        muted: AppColors.lightMuted,
        mutedForeground: AppColors.lightMutedForeground,
        border: AppColors.lightBorder,
        destructive: AppColors.destructiveLight,
      );

  static ThemeData get dark => _build(
        brightness: Brightness.dark,
        background: AppColors.darkBackground,
        foreground: AppColors.darkForeground,
        primary: AppColors.darkPrimary,
        card: AppColors.darkCard,
        muted: AppColors.darkMuted,
        mutedForeground: AppColors.darkMutedForeground,
        border: AppColors.darkBorder,
        destructive: AppColors.destructiveDark,
      );

  static ThemeData _build({
    required Brightness brightness,
    required Color background,
    required Color foreground,
    required Color primary,
    required Color card,
    required Color muted,
    required Color mutedForeground,
    required Color border,
    required Color destructive,
  }) {
    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: primary,
      onPrimary: Colors.white,
      secondary: primary,
      onSecondary: Colors.white,
      error: destructive,
      onError: Colors.white,
      surface: card,
      onSurface: foreground,
      surfaceContainerHighest: muted,
      onSurfaceVariant: mutedForeground,
      outline: border,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: background,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: foreground,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: card,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: destructive),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: primary),
      ),
      dividerTheme: DividerThemeData(color: border, space: 1),
    );
  }
}
