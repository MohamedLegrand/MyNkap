import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/auth_tokens.dart';
import '../../../core/network/token_refresher.dart';
import '../domain/client.dart';

/// Appels HTTP bruts du module auth — aucune logique métier ni stockage
/// ici (voir AuthRepository), seulement la traduction requête/réponse.
/// Utilise [dioNuProvider] (jamais [dioProvider]) : aucune de ces routes
/// ne doit poser de jeton ni tenter un rafraîchissement automatique — soit
/// parce qu'aucune session n'existe encore (register/login/verify-otp),
/// soit parce que la route gère elle-même son jeton (refresh, logout).
class AuthApi {
  AuthApi(this._dio);

  final Dio _dio;

  Future<int> register({
    required String email,
    required String motDePasse,
    required String firstName,
    required String lastName,
    required String phone,
  }) async {
    final reponse = await _dio.post(
      ApiEndpoints.register,
      data: {
        'email': email,
        'mot_de_passe': motDePasse,
        'first_name': firstName,
        'last_name': lastName,
        'phone': phone,
      },
    );
    return (reponse.data as Map<String, dynamic>)['expires_in'] as int;
  }

  Future<void> verifyOtp({required String email, required String code}) async {
    await _dio.post(
      ApiEndpoints.verifyOtp,
      data: {'email': email, 'code': code},
    );
  }

  Future<AuthTokens> login({
    required String email,
    required String motDePasse,
  }) async {
    final reponse = await _dio.post(
      ApiEndpoints.login,
      data: {'email': email, 'mot_de_passe': motDePasse},
    );
    return AuthTokens.fromJson(reponse.data as Map<String, dynamic>);
  }

  Future<void> logout(String refreshToken) async {
    await _dio.post(ApiEndpoints.logout, data: {'refresh_token': refreshToken});
  }

  /// POST /auth/refresh — [AuthRepository.deverrouillerAvecBiometrie] ne
  /// fait rien d'autre que rejouer ce même appel une fois la présence de
  /// l'utilisateur confirmée localement (empreinte/Face ID) : aucune route
  /// dédiée n'est nécessaire côté backend. Partage l'implémentation avec
  /// [AuthInterceptor] (rafraîchissement silencieux sur 401) via
  /// [rafraichirJetons] — jamais deux appels à /auth/refresh écrits à la main.
  Future<AuthTokens> refresh(String refreshToken) => rafraichirJetons(_dio, refreshToken);

  Future<void> forgotPassword(String email) async {
    await _dio.post(ApiEndpoints.forgotPassword, data: {'email': email});
  }

  Future<void> resetPassword({
    required String token,
    required String nouveauMotDePasse,
  }) async {
    await _dio.post(
      ApiEndpoints.resetPassword,
      data: {'token': token, 'nouveau_mot_de_passe': nouveauMotDePasse},
    );
  }

  /// GET /auth/me exige un jeton d'accès valide : passe par [dioProvider]
  /// (jamais [dioNuProvider]) pour bénéficier de la pose automatique du
  /// jeton — seul appel de cette classe dans ce cas, voir [meAvecDioAuthentifie].
  Future<Client> meAvecDioAuthentifie(Dio dioAuthentifie) async {
    final reponse = await dioAuthentifie.get(ApiEndpoints.me);
    return Client.fromJson(reponse.data as Map<String, dynamic>);
  }
}

final authApiProvider = Provider<AuthApi>((ref) => AuthApi(ref.watch(dioNuProvider)));
