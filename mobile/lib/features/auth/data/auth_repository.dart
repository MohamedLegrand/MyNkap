import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/storage/secure_storage.dart';
import '../domain/client.dart';
import 'auth_api.dart';

/// Erreur métier : identifiants valides, mais le compte est un compte
/// administrateur — l'app mobile ne sert que les clients (voir
/// AuthTokens.userType et le dashboard admin, resté web-only).
class CompteAdminNonSupporteException implements Exception {
  const CompteAdminNonSupporteException();

  @override
  String toString() =>
      "Ce compte est un compte administrateur : connectez-vous depuis le site web.";
}

/// Orchestration du module auth : appelle [AuthApi], gère le stockage
/// sécurisé de la session (voir SecureStorage) — la seule couche qui a le
/// droit d'écrire/lire les jetons, jamais les écrans directement.
class AuthRepository {
  AuthRepository(this._api, this._dioAuthentifie);

  final AuthApi _api;
  final Dio _dioAuthentifie;

  Future<int> register({
    required String email,
    required String motDePasse,
    required String firstName,
    required String lastName,
    required String phone,
  }) {
    return _api.register(
      email: email,
      motDePasse: motDePasse,
      firstName: firstName,
      lastName: lastName,
      phone: phone,
    );
  }

  Future<void> verifyOtp({required String email, required String code}) {
    return _api.verifyOtp(email: email, code: code);
  }

  /// Connecte le client et persiste la session — lève
  /// [CompteAdminNonSupporteException] sans rien stocker si les
  /// identifiants appartiennent à un compte administrateur.
  Future<Client> login({required String email, required String motDePasse}) async {
    final jetons = await _api.login(email: email, motDePasse: motDePasse);
    if (jetons.userType != 'client') {
      throw const CompteAdminNonSupporteException();
    }

    await SecureStorage.enregistrerSession(
      accessToken: jetons.accessToken,
      refreshToken: jetons.refreshToken,
      typeUtilisateur: jetons.userType,
    );

    return _api.meAvecDioAuthentifie(_dioAuthentifie);
  }

  /// Restaure une session existante au démarrage de l'app (voir
  /// AuthController) — renvoie null si aucun jeton n'est stocké ou si le
  /// jeton stocké n'est plus valide (auquel cas la session locale est
  /// effacée : mieux vaut redemander une connexion qu'un état incohérent).
  Future<Client?> restaurerSession() async {
    final accessToken = await SecureStorage.lireAccessToken();
    if (accessToken == null) return null;

    try {
      return await _api.meAvecDioAuthentifie(_dioAuthentifie);
    } catch (_) {
      await SecureStorage.effacerSession();
      return null;
    }
  }

  Future<void> logout() async {
    final refreshToken = await SecureStorage.lireRefreshToken();
    if (refreshToken != null) {
      try {
        await _api.logout(refreshToken);
      } catch (_) {
        // La révocation côté serveur a échoué (réseau, jeton déjà expiré...) :
        // on efface quand même la session locale, jamais bloquant pour le client.
      }
    }
    await SecureStorage.effacerSession();
  }

  Future<void> forgotPassword(String email) => _api.forgotPassword(email);

  Future<void> resetPassword({
    required String token,
    required String nouveauMotDePasse,
  }) {
    return _api.resetPassword(token: token, nouveauMotDePasse: nouveauMotDePasse);
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(authApiProvider), ref.watch(dioProvider));
});
