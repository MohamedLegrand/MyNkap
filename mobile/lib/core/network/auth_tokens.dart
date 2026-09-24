/// Miroir de `TokenResponse` (backend/app/modules/auth/schemas.py) —
/// renvoyé par /auth/login, /auth/google et /auth/refresh.
class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.userType,
  });

  final String accessToken;
  final String refreshToken;

  /// "client" ou "administrateur" — l'app mobile ne sert que les clients,
  /// mais on garde le champ pour refuser explicitement une connexion admin
  /// plutôt que d'échouer silencieusement plus loin (voir AuthRepository.login).
  final String userType;

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      userType: json['user_type'] as String,
    );
  }
}
