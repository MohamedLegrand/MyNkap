import 'package:dio/dio.dart';

import '../constants/api_endpoints.dart';
import 'auth_tokens.dart';

/// Rejoue POST /auth/refresh — partagé par [AuthInterceptor]
/// (rafraîchissement silencieux sur 401) et par le déverrouillage
/// biométrique (voir features/auth/data/auth_repository.dart), qui ne
/// fait rien d'autre que rejouer ce même appel une fois la présence de
/// l'utilisateur confirmée localement : une seule implémentation de
/// l'appel réseau, jamais recopiée.
Future<AuthTokens> rafraichirJetons(Dio dioSansIntercepteur, String refreshToken) async {
  final reponse = await dioSansIntercepteur.post(
    ApiEndpoints.refresh,
    data: {'refresh_token': refreshToken},
  );
  return AuthTokens.fromJson(reponse.data as Map<String, dynamic>);
}
