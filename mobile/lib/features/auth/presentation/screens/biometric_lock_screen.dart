import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/auth_repository.dart';
import '../controllers/app_lock_controller.dart';
import '../controllers/auth_controller.dart';

/// Affiché à la place du tableau de bord tant que [appLockProvider] est à
/// `false` (voir AppRouter) — la session est déjà techniquement valide
/// (restaurée en silence par AuthController), mais l'accès reste bloqué
/// jusqu'à une vérification biométrique réussie.
class BiometricLockScreen extends ConsumerStatefulWidget {
  const BiometricLockScreen({super.key});

  @override
  ConsumerState<BiometricLockScreen> createState() => _BiometricLockScreenState();
}

class _BiometricLockScreenState extends ConsumerState<BiometricLockScreen> {
  bool _isLoading = false;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    // Invite biométrique automatique à l'arrivée sur l'écran — l'utilisateur
    // n'a rien à faire pour la déclencher la première fois, seulement pour
    // réessayer après un échec (voir _deverrouiller ci-dessous).
    WidgetsBinding.instance.addPostFrameCallback((_) => _deverrouiller());
  }

  Future<void> _deverrouiller() async {
    setState(() {
      _isLoading = true;
      _erreur = null;
    });
    try {
      await ref.read(authRepositoryProvider).deverrouillerAvecBiometrie();
      if (!mounted) return;
      ref.read(appLockProvider.notifier).deverrouiller();
    } on SessionExpireeException catch (erreur) {
      // Le refresh token n'est plus valide : impossible de rester sur cet
      // écran, seule une reconnexion par mot de passe peut réparer ça.
      await ref.read(authControllerProvider.notifier).logout();
      if (mounted) setState(() => _erreur = erreur.toString());
    } catch (_) {
      if (mounted) {
        setState(() => _erreur = 'Vérification biométrique impossible. Réessayez.');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.fingerprint,
                  size: 72,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(height: 20),
                const Text(
                  'MyNkap est verrouillé',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                Text(
                  'Déverrouillez avec votre empreinte ou Face ID.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 24),
                if (_erreur != null) ...[
                  Text(
                    _erreur!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                  const SizedBox(height: 16),
                ],
                FilledButton.icon(
                  onPressed: _isLoading ? null : _deverrouiller,
                  icon: _isLoading
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.lock_open),
                  label: const Text('Déverrouiller'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => ref.read(authControllerProvider.notifier).logout(),
                  child: const Text('Se déconnecter'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
