import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/controllers/app_lock_controller.dart';
import '../../features/auth/presentation/controllers/auth_controller.dart';
import '../../features/auth/presentation/screens/biometric_lock_screen.dart';
import '../../features/auth/presentation/screens/forgot_password_screen.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/screens/otp_screen.dart';
import '../../features/auth/presentation/screens/register_screen.dart';
import '../../features/auth/presentation/screens/security_settings_screen.dart';
import '../../features/auth/presentation/screens/splash_screen.dart';
import '../../features/dashboard/presentation/screens/home_screen.dart';
import 'app_routes.dart';

/// Relaie les changements de [authControllerProvider] et [appLockProvider]
/// à [GoRouter] (`refreshListenable` exige un `Listenable`, pas un
/// `ProviderListenable`) pour que la redirection se réévalue dès que la
/// session ou le verrou biométrique changent — sans ça, se connecter ou se
/// déverrouiller resterait bloqué jusqu'à une navigation manuelle qui
/// redéclenche `redirect`.
class _EcouteurNavigation extends ChangeNotifier {
  _EcouteurNavigation(Ref ref) {
    ref.listen(authControllerProvider, (_, _) => notifyListeners());
    ref.listen(appLockProvider, (_, _) => notifyListeners());
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final ecouteurNavigation = _EcouteurNavigation(ref);
  ref.onDispose(ecouteurNavigation.dispose);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    refreshListenable: ecouteurNavigation,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final chemin = state.matchedLocation;

      // Restauration de session en cours (voir AuthController.build) :
      // reste sur /splash, jamais de redirection prématurée.
      if (authState.isLoading) {
        return chemin == AppRoutes.splash ? null : AppRoutes.splash;
      }

      const cheminsPublics = {
        AppRoutes.login,
        AppRoutes.register,
        AppRoutes.verifyOtp,
        AppRoutes.forgotPassword,
      };

      final estConnecte = authState.value != null;
      if (!estConnecte) {
        return cheminsPublics.contains(chemin) ? null : AppRoutes.login;
      }

      // Connecté à partir d'ici : le verrou biométrique est prioritaire sur
      // tout le reste, y compris les chemins publics ou /splash — voir
      // AppLockController (jamais posé si la biométrie est désactivée).
      if (!ref.read(appLockProvider)) {
        return chemin == AppRoutes.biometricLock ? null : AppRoutes.biometricLock;
      }
      final doitRejoindreAccueil = chemin == AppRoutes.splash ||
          chemin == AppRoutes.biometricLock ||
          cheminsPublics.contains(chemin);
      return doitRejoindreAccueil ? AppRoutes.home : null;
    },
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => LoginScreen(messageInitial: state.extra as String?),
      ),
      GoRoute(
        path: AppRoutes.register,
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: AppRoutes.verifyOtp,
        builder: (context, state) => OtpScreen(email: state.extra as String),
      ),
      GoRoute(
        path: AppRoutes.forgotPassword,
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: AppRoutes.biometricLock,
        builder: (context, state) => const BiometricLockScreen(),
      ),
      GoRoute(
        path: AppRoutes.home,
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: AppRoutes.security,
        builder: (context, state) => const SecuritySettingsScreen(),
      ),
    ],
  );
});
