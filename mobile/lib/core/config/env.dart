import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Lit la configuration chargée depuis `.env` par [main] au démarrage (voir
/// `.env.example`). Une seule façade statique plutôt qu'un accès direct à
/// `dotenv.env[...]` dispersé dans le code : centralise les valeurs par
/// défaut et le nom exact des clés.
class Env {
  Env._();

  static String get apiBaseUrl =>
      dotenv.env['API_BASE_URL'] ?? 'http://10.0.2.2:8000/api/v1';

  static String get googleClientId => dotenv.env['GOOGLE_CLIENT_ID'] ?? '';
}
