import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Stockage des jetons de session (Keychain iOS / Keystore Android via
/// flutter_secure_storage) — contrairement au web, qui garde les jetons en
/// `localStorage` (voir frontend/src/store, `mynkap-auth`) faute de mieux
/// dans un navigateur, le stockage sécurisé natif protège ici les jetons
/// même en cas de faille dans l'app (pas de lecture arbitraire depuis un
/// autre process, contrairement à `localStorage` qu'un XSS peut lire).
class SecureStorage {
  SecureStorage._();

  // Options par défaut : AES-GCM 256 bits avec clé protégée par RSA-OAEP
  // (Android Keystore) / Keychain iOS — déjà le stockage le plus sûr offert
  // par le paquet, rien à personnaliser ici.
  static const _storage = FlutterSecureStorage();

  static const _cleAccessToken = 'access_token';
  static const _cleRefreshToken = 'refresh_token';
  static const _cleTypeUtilisateur = 'user_type';
  static const _cleBiometrieActive = 'biometric_enabled';

  static Future<void> enregistrerSession({
    required String accessToken,
    required String refreshToken,
    required String typeUtilisateur,
  }) async {
    await Future.wait([
      _storage.write(key: _cleAccessToken, value: accessToken),
      _storage.write(key: _cleRefreshToken, value: refreshToken),
      _storage.write(key: _cleTypeUtilisateur, value: typeUtilisateur),
    ]);
  }

  static Future<String?> lireAccessToken() => _storage.read(key: _cleAccessToken);

  static Future<String?> lireRefreshToken() => _storage.read(key: _cleRefreshToken);

  static Future<String?> lireTypeUtilisateur() =>
      _storage.read(key: _cleTypeUtilisateur);

  /// Met à jour uniquement l'access token (et éventuellement le refresh
  /// token, qui tourne à chaque appel à /auth/refresh côté backend — voir
  /// auth.services.faire_tourner_refresh_token) sans toucher au reste de la
  /// session.
  static Future<void> mettreAJourJetons({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(key: _cleAccessToken, value: accessToken),
      _storage.write(key: _cleRefreshToken, value: refreshToken),
    ]);
  }

  /// Efface toute la session, y compris la préférence de connexion
  /// biométrique — sans jeton à déverrouiller, l'activer n'aurait plus de
  /// sens : la prochaine connexion repart sur un choix explicite (voir
  /// AuthRepository.activerBiometrie).
  static Future<void> effacerSession() => _storage.deleteAll();

  /// Préférence client : déverrouiller l'app avec l'empreinte/Face ID au
  /// lieu du mot de passe. Ne conditionne jamais l'accès à elle seule —
  /// voir AuthRepository.deverrouillerAvecBiometrie, qui exige toujours une
  /// vérification biométrique réussie avant de réutiliser le refresh token.
  static Future<void> activerBiometrie() =>
      _storage.write(key: _cleBiometrieActive, value: 'true');

  static Future<void> desactiverBiometrie() => _storage.delete(key: _cleBiometrieActive);

  static Future<bool> biometrieEstActive() async =>
      (await _storage.read(key: _cleBiometrieActive)) == 'true';
}
