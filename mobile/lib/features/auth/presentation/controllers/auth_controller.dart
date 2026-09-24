import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/session_manager.dart';
import '../../../../core/storage/secure_storage.dart';
import '../../data/auth_repository.dart';
import '../../domain/client.dart';
import 'app_lock_controller.dart';

/// État de session unique pour toute l'app : `AsyncLoading` pendant la
/// restauration au démarrage (voir [build]), `AsyncData(null)` = déconnecté,
/// `AsyncData(client)` = connecté. [AppRouter] redirige uniquement sur ces
/// trois états — jamais de booléen `isLoggedIn` séparé à faire dériver.
class AuthController extends AsyncNotifier<Client?> {
  @override
  Future<Client?> build() async {
    // Le rafraîchissement automatique (voir AuthInterceptor) peut échouer
    // bien après le démarrage (refresh token expiré au bout de 8 jours,
    // révoqué par un admin...) : SessionManager relaie cet événement ici
    // pour que toute l'app retombe immédiatement en état déconnecté,
    // plutôt que de laisser des écrans authentifiés continuer d'appeler une
    // API qui répond 401 en boucle.
    SessionManager.enregistrerEcouteur(() {
      state = const AsyncData(null);
    });

    final client = await ref.read(authRepositoryProvider).restaurerSession();
    // Verrouille seulement quand une session existante vient d'être
    // restaurée au démarrage à froid ET que le client a activé la
    // biométrie — une connexion interactive réussie (voir [login]) prouve
    // déjà la présence de l'utilisateur, inutile de la redemander aussitôt.
    if (client != null && await SecureStorage.biometrieEstActive()) {
      ref.read(appLockProvider.notifier).verrouiller();
    }
    return client;
  }

  Future<void> login({required String email, required String motDePasse}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).login(email: email, motDePasse: motDePasse),
    );
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    ref.read(appLockProvider.notifier).deverrouiller();
    state = const AsyncData(null);
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, Client?>(
  AuthController.new,
);
