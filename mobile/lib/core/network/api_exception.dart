import 'package:dio/dio.dart';

/// Erreur applicative normalisée à partir d'une [DioException] — le
/// backend répond toujours `{"detail": "message en français"}` sur une
/// erreur (voir `app.core.exceptions.MyNkapException` et les
/// `HTTPException` FastAPI), jamais une autre forme : cette classe évite
/// de reparser ça à chaque appel, comme le fait `services/api.ts` côté
/// frontend.
class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  factory ApiException.fromDioException(DioException erreur) {
    final reponse = erreur.response;
    if (reponse != null) {
      final donnees = reponse.data;
      final detail = donnees is Map ? donnees['detail'] : null;
      if (detail is String && detail.isNotEmpty) {
        return ApiException(detail, statusCode: reponse.statusCode);
      }
      return ApiException(
        'Une erreur est survenue (${reponse.statusCode}).',
        statusCode: reponse.statusCode,
      );
    }

    if (erreur.type == DioExceptionType.connectionTimeout ||
        erreur.type == DioExceptionType.receiveTimeout ||
        erreur.type == DioExceptionType.sendTimeout) {
      return const ApiException('La connexion au serveur a expiré. Réessayez.');
    }
    if (erreur.type == DioExceptionType.connectionError) {
      return const ApiException(
        'Impossible de joindre le serveur. Vérifiez votre connexion.',
      );
    }
    return ApiException(erreur.message ?? 'Une erreur inattendue est survenue.');
  }

  @override
  String toString() => message;
}
