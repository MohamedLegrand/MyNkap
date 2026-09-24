import 'package:flutter/material.dart';

/// Palette MyNkap — recopiée depuis `frontend/tailwind.config.js` et
/// `frontend/src/index.css` (variables `--primary`, `--background`, etc.)
/// pour que l'app mobile ait la même identité visuelle que le web, sans
/// dépendre de Tailwind ici. Toute évolution de palette côté web doit être
/// reportée ici à la main (aucune source commune entre les deux stacks).
class AppColors {
  AppColors._();

  // Vert forêt — couleur de marque, identique aux deux thèmes (primary =
  // secondary côté web, voir index.css).
  static const forest50 = Color(0xFFF2F8F3);
  static const forest100 = Color(0xFFE1EFE3);
  static const forest200 = Color(0xFFC4DEC7);
  static const forest300 = Color(0xFF98C39E);
  static const forest400 = Color(0xFF67A16E);
  static const forest500 = Color(0xFF42834A);
  static const forest600 = Color(0xFF316938);
  static const forest700 = Color(0xFF254E2A);
  static const forest800 = Color(0xFF203F23);
  static const forest900 = Color(0xFF1B321E);

  // Thème clair
  static const lightBackground = Color(0xFFF7F9F5);
  static const lightForeground = Color(0xFF0B1220);
  static const lightPrimary = forest700;
  static const lightCard = Color(0xFFFFFFFF);
  static const lightMuted = Color(0xFFEFF2ED);
  static const lightMutedForeground = Color(0xFF5B6B5D);
  static const lightBorder = Color(0xFFE2E8DE);

  // Thème sombre
  static const darkBackground = Color(0xFF020617);
  static const darkForeground = Color(0xFFF8FAFC);
  static const darkPrimary = forest500;
  static const darkCard = Color(0xFF0B1220);
  static const darkMuted = Color(0xFF111827);
  static const darkMutedForeground = Color(0xFF94A3B8);
  static const darkBorder = Color(0xFF1E293B);

  // Destructif (erreurs, montants négatifs) — identique aux deux thèmes.
  static const destructiveLight = Color(0xFFEF4444);
  static const destructiveDark = Color(0xFF7F1D1D);
}
