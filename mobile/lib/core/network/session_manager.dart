import 'package:flutter/foundation.dart';

/// Point de contact entre la couche réseau (`core`, qui ne doit jamais
/// dépendre d'une feature) et la session applicative (`features/auth`) :
/// quand [AuthInterceptor] échoue à rafraîchir le jeton d'accès (refresh
/// token lui-même expiré/révoqué), il appelle [notifierExpiration] plutôt
/// que d'importer directement le contrôleur d'authentification. C'est
/// `AuthController` qui s'enregistre ici au démarrage (voir
/// `features/auth/presentation/controllers/auth_controller.dart`) —
/// mêmes rôles que `useAuthStore.getState().logout()` appelé depuis
/// `services/api.ts` côté frontend.
class SessionManager {
  SessionManager._();

  static VoidCallback? _surExpiration;

  static void enregistrerEcouteur(VoidCallback ecouteur) {
    _surExpiration = ecouteur;
  }

  static void notifierExpiration() {
    _surExpiration?.call();
  }
}
