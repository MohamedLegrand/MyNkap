import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

/// Enveloppe autour de `local_auth` — la seule classe de l'app à parler
/// directement au capteur biométrique. `biometricOnly: false` dans
/// [authentifier] laisse l'OS proposer le code/schéma de l'appareil en
/// repli si l'empreinte/Face ID échoue ou n'est pas configuré : mieux
/// qu'un blocage complet pour un client qui a activé l'option mais dont le
/// capteur est temporairement indisponible (doigt mouillé, etc.).
class BiometricService {
  final _localAuth = LocalAuthentication();

  /// L'appareil peut-il proposer une vérification biométrique ou, à
  /// défaut, un code/schéma ? Vérifié avant de proposer l'option dans les
  /// réglages (voir SecuritySettingsScreen) — inutile d'afficher un
  /// interrupteur qui échouerait à coup sûr.
  Future<bool> appareilCompatible() async {
    try {
      final supporte = await _localAuth.isDeviceSupported();
      final peutVerifier = await _localAuth.canCheckBiometrics;
      return supporte || peutVerifier;
    } catch (_) {
      return false;
    }
  }

  /// Déclenche l'invite native et renvoie `true` seulement si
  /// l'utilisateur a réussi la vérification (jamais sur annulation ou
  /// erreur — voir les appelants, qui ne doivent alors ni activer la
  /// biométrie ni réutiliser le refresh token).
  Future<bool> authentifier(String raison) async {
    try {
      return await _localAuth.authenticate(
        localizedReason: raison,
        biometricOnly: false,
        persistAcrossBackgrounding: true,
      );
    } catch (_) {
      return false;
    }
  }
}

final biometricServiceProvider = Provider<BiometricService>((ref) => BiometricService());
