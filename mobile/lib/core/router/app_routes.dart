/// Chemins de navigation — une constante par écran, jamais une chaîne
/// recopiée à la main dans un `context.go(...)` (même principe que
/// [ApiEndpoints] pour les routes API).
class AppRoutes {
  AppRoutes._();

  static const splash = '/splash';
  static const login = '/login';
  static const register = '/register';
  static const verifyOtp = '/verify-otp';
  static const forgotPassword = '/forgot-password';
  static const biometricLock = '/lock';
  static const home = '/home';
  static const security = '/settings/security';
}
