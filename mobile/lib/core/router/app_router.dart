import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/controllers/auth_controller.dart';
import '../../features/auth/presentation/screens/forgot_password_screen.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/screens/otp_screen.dart';
import '../../features/auth/presentation/screens/register_screen.dart';
import '../../features/auth/presentation/screens/splash_screen.dart';
import '../../features/dashboard/presentation/screens/home_screen.dart';
import 'app_routes.dart';

/// Relaie les changements de [authControllerProvider] à [GoRouter]
/// (`refreshListenable` exige un `Listenable`, pas un `ProviderListenable`)
/// pour que la redirection se réévalue dès que la session change — sans
/// ça, se connecter resterait bloqué sur /login jusqu'à une navigation
/// manuelle qui redéclenche `redirect`.
class _EcouteurAuth extends ChangeNotifier {
  _EcouteurAuth(Ref ref) {
    ref.listen(authControllerProvider, (_, _) => notifyListeners());
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  final ecouteurAuth = _EcouteurAuth(ref);
  ref.onDispose(ecouteurAuth.dispose);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    refreshListenable: ecouteurAuth,
    redirect: (context, state) {
      final authState = ref.read(authControllerProvider);
      final chemin = state.matchedLocation;

      // Restauration de session en cours (voir AuthController.build) :
      // reste sur /splash, jamais de redirection prématurée.
      if (authState.isLoading) {
        return chemin == AppRoutes.splash ? null : AppRoutes.splash;
      }

      final estConnecte = authState.value != null;
      const cheminsPublics = {
        AppRoutes.login,
        AppRoutes.register,
        AppRoutes.verifyOtp,
        AppRoutes.forgotPassword,
      };

      if (!estConnecte && !cheminsPublics.contains(chemin)) {
        return AppRoutes.login;
      }
      if (estConnecte && (cheminsPublics.contains(chemin) || chemin == AppRoutes.splash)) {
        return AppRoutes.home;
      }
      // Toujours quitter /splash une fois l'état de session connu, même
      // déconnecté (sinon un utilisateur non connecté resterait bloqué
      // dessus : /login est un chemin public, donc la règle précédente ne
      // le redirige pas).
      if (chemin == AppRoutes.splash) {
        return AppRoutes.login;
      }
      return null;
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
        path: AppRoutes.home,
        builder: (context, state) => const HomeScreen(),
      ),
    ],
  );
});
