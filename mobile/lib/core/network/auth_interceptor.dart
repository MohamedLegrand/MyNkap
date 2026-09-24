import 'package:dio/dio.dart';

import '../constants/api_endpoints.dart';
import '../storage/secure_storage.dart';
import 'session_manager.dart';
import 'token_refresher.dart';

/// Endpoints d'authentification eux-mêmes : jamais de tentative de
/// rafraîchissement automatique dessus (un 401 y a un sens propre — ex.
/// mauvais mot de passe — et retenter via /auth/refresh boucherait sans
/// fin si le refresh token est lui aussi invalide). Même liste que
/// `ROUTES_AUTH_SANS_RETRY` dans `frontend/src/services/api.ts`.
const _routesAuthSansRetry = [
  ApiEndpoints.login,
  ApiEndpoints.loginGoogle,
  ApiEndpoints.verifyOtp,
  ApiEndpoints.refresh,
  ApiEndpoints.register,
];

/// Pose le jeton d'accès sur chaque requête et, sur un 401, tente un seul
/// rafraîchissement avant de renvoyer la requête d'origine — `QueuedInterceptor`
/// garantit qu'un seul rafraîchissement part si plusieurs requêtes essuient un
/// 401 en même temps, les autres attendent la même réponse (équivalent de la
/// promesse partagée `rafraichissementEnCours` côté frontend).
class AuthInterceptor extends QueuedInterceptor {
  AuthInterceptor(this._dioSansIntercepteur);

  /// Instance Dio nue (aucun intercepteur), dédiée à l'appel de
  /// /auth/refresh — évite toute récursion si cet appel échouait lui aussi
  /// en 401.
  final Dio _dioSansIntercepteur;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final accessToken = await SecureStorage.lireAccessToken();
    if (accessToken != null) {
      options.headers['Authorization'] = 'Bearer $accessToken';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final requete = err.requestOptions;
    final estRouteSansRetry =
        _routesAuthSansRetry.any((route) => requete.path.startsWith(route));

    if (err.response?.statusCode != 401 || estRouteSansRetry) {
      handler.next(err);
      return;
    }

    final nouvelAccessToken = await _rafraichir();
    if (nouvelAccessToken == null) {
      await SecureStorage.effacerSession();
      SessionManager.notifierExpiration();
      handler.next(err);
      return;
    }

    try {
      requete.headers['Authorization'] = 'Bearer $nouvelAccessToken';
      final reponse = await _dioSansIntercepteur.fetch(requete);
      handler.resolve(reponse);
    } on DioException catch (erreurRetry) {
      handler.next(erreurRetry);
    }
  }

  Future<String?> _rafraichir() async {
    final refreshToken = await SecureStorage.lireRefreshToken();
    if (refreshToken == null) return null;

    try {
      final jetons = await rafraichirJetons(_dioSansIntercepteur, refreshToken);

      // Le refresh token tourne à chaque appel côté backend (l'ancien est
      // révoqué) : il faut impérativement stocker le nouveau, sous peine de
      // session bloquée au prochain rafraîchissement.
      await SecureStorage.mettreAJourJetons(
        accessToken: jetons.accessToken,
        refreshToken: jetons.refreshToken,
      );
      return jetons.accessToken;
    } on DioException {
      return null;
    }
  }
}
