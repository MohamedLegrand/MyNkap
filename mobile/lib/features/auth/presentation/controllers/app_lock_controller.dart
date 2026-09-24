import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Verrou d'écran distinct de la session (voir [AuthController]) : une
/// session peut rester techniquement valide (jeton rafraîchi en silence)
/// alors que l'app doit quand même redemander une preuve de présence —
/// c'est tout l'intérêt de la biométrie sur mobile. `true` par défaut
/// (déverrouillé) : ne concerne que les cas où la biométrie est active ET
/// qu'une session vient d'être restaurée au démarrage à froid, voir
/// AuthController.build, qui verrouille explicitement dans ce cas précis
/// — jamais après une connexion interactive par mot de passe, déjà une
/// preuve de présence suffisante.
class AppLockController extends Notifier<bool> {
  @override
  bool build() => true;

  void verrouiller() => state = false;

  void deverrouiller() => state = true;
}

final appLockProvider = NotifierProvider<AppLockController, bool>(AppLockController.new);
