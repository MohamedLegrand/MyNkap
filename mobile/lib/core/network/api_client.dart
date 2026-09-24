import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/env.dart';
import 'auth_interceptor.dart';

const _delaiConnexion = Duration(seconds: 15);
const _delaiReponse = Duration(seconds: 20);

Dio _construireDio() {
  return Dio(
    BaseOptions(
      baseUrl: Env.apiBaseUrl,
      connectTimeout: _delaiConnexion,
      receiveTimeout: _delaiReponse,
      contentType: 'application/json',
    ),
  );
}

/// Dio "nu", sans intercepteur — utilisé par [AuthInterceptor] pour l'appel
/// à /auth/refresh (jamais rejouer l'intercepteur sur lui-même) et par les
/// écrans d'authentification eux-mêmes (login/register/OTP : aucun jeton à
/// poser, aucun 401 à rattraper).
final dioNuProvider = Provider<Dio>((ref) => _construireDio());

/// Dio applicatif : jeton d'accès posé automatiquement, rafraîchissement
/// transparent sur 401 (voir [AuthInterceptor]) — celui que consomment tous
/// les repositories des features protégées (comptes, transactions...).
final dioProvider = Provider<Dio>((ref) {
  final dio = _construireDio();
  dio.interceptors.add(AuthInterceptor(ref.watch(dioNuProvider)));
  return dio;
});
