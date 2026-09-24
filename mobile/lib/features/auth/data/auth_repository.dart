import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/biometrics/biometric_service.dart';
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

/// La vérification biométrique elle-même a échoué ou a été annulée —
/// distinct d'une session expirée (voir [SessionExpireeException]) : dans
/// ce cas, il reste possible de réessayer sans se déconnecter.
class BiometrieEchoueeException implements Exception {
  const BiometrieEchoueeException();

  @override
  String toString() => 'Vérification biométrique impossible.';
}

/// La biométrie a réussi, mais le refresh token stocké n'est plus valide
/// (expiré après 8 jours, révoqué par un admin...) : contrairement à
/// [BiometrieEchoueeException], réessayer ne suffit pas, une reconnexion
/// complète est nécessaire — voir BiometricLockScreen.
class SessionExpireeException implements Exception {
  const SessionExpireeException();

  @override
  String toString() => 'Votre session a expiré. Reconnectez-vous.';
}

/// Orchestration du module auth : appelle [AuthApi], gère le stockage
/// sécurisé de la session (voir SecureStorage) — la seule couche qui a le
/// droit d'écrire/lire les jetons, jamais les écrans directement.
class AuthRepository {
  AuthRepository(this._api, this._dioAuthentifie, this._biometrie);

  final AuthApi _api;
  final Dio _dioAuthentifie;
  final BiometricService _biometrie;

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

  // --- Connexion biométrique ---
  //
  // Ne remplace pas la connexion par mot de passe : elle déverrouille
  // localement une session déjà ouverte (le refresh token en cours,
  // toujours stocké — voir SecureStorage). Aucune route backend dédiée :
  // le déverrouillage rejoue simplement POST /auth/refresh une fois la
  // présence de l'utilisateur confirmée par le capteur — la même garantie
  // que le backend applique déjà à toute rotation de refresh token
  // (voir auth.services.faire_tourner_refresh_token).

  Future<bool> biometrieDisponibleSurAppareil() => _biometrie.appareilCompatible();

  Future<bool> biometrieEstActive() => SecureStorage.biometrieEstActive();

  /// Active la connexion biométrique — exige toujours une vérification
  /// réussie avant d'enregistrer la préférence, jamais activée à
  /// l'aveugle : un interrupteur "activé" doit garantir que le capteur a
  /// réellement reconnu l'utilisateur au moins une fois.
  Future<void> activerBiometrie() async {
    final reussi = await _biometrie.authentifier(
      'Confirmez votre identité pour activer la connexion biométrique',
    );
    if (!reussi) throw const BiometrieEchoueeException();
    await SecureStorage.activerBiometrie();
  }

  Future<void> desactiverBiometrie() => SecureStorage.desactiverBiometrie();

  /// Déverrouille une session existante avec l'empreinte/Face ID — voir
  /// [BiometricLockScreen]. Lève [BiometrieEchoueeException] si la
  /// vérification échoue (l'utilisateur peut réessayer) ou
  /// [SessionExpireeException] si le refresh token stocké n'est plus
  /// valide (il faut alors se reconnecter par mot de passe).
  Future<Client> deverrouillerAvecBiometrie() async {
    final reussi = await _biometrie.authentifier('Déverrouillez MyNkap');
    if (!reussi) throw const BiometrieEchoueeException();

    final refreshToken = await SecureStorage.lireRefreshToken();
    if (refreshToken == null) throw const SessionExpireeException();

    try {
      final jetons = await _api.refresh(refreshToken);
      await SecureStorage.mettreAJourJetons(
        accessToken: jetons.accessToken,
        refreshToken: jetons.refreshToken,
      );
      return await _api.meAvecDioAuthentifie(_dioAuthentifie);
    } on DioException {
      await SecureStorage.effacerSession();
      throw const SessionExpireeException();
    }
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    ref.watch(authApiProvider),
    ref.watch(dioProvider),
    ref.watch(biometricServiceProvider),
  );
});
