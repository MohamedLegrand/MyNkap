import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/auth_repository.dart';

/// Réglages de sécurité du compte — pour l'instant, seulement la
/// connexion biométrique. Reste dans le module auth (pas dans
/// features/settings/) : c'est une préférence de session, pas un réglage
/// applicatif général (devise, langue...).
class SecuritySettingsScreen extends ConsumerStatefulWidget {
  const SecuritySettingsScreen({super.key});

  @override
  ConsumerState<SecuritySettingsScreen> createState() => _SecuritySettingsScreenState();
}

class _SecuritySettingsScreenState extends ConsumerState<SecuritySettingsScreen> {
  bool _chargement = true;
  bool _compatible = false;
  bool _active = false;
  bool _enCours = false;
  String? _erreur;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    final repo = ref.read(authRepositoryProvider);
    final compatible = await repo.biometrieDisponibleSurAppareil();
    final active = await repo.biometrieEstActive();
    if (!mounted) return;
    setState(() {
      _compatible = compatible;
      _active = active;
      _chargement = false;
    });
  }

  Future<void> _basculer(bool nouvelleValeur) async {
    setState(() {
      _enCours = true;
      _erreur = null;
    });
    final repo = ref.read(authRepositoryProvider);
    try {
      if (nouvelleValeur) {
        await repo.activerBiometrie();
      } else {
        await repo.desactiverBiometrie();
      }
      if (mounted) setState(() => _active = nouvelleValeur);
    } catch (erreur) {
      if (mounted) {
        setState(() => _erreur = erreur is BiometrieEchoueeException
            ? erreur.toString()
            : 'Impossible de modifier ce réglage.');
      }
    } finally {
      if (mounted) setState(() => _enCours = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sécurité')),
      body: _chargement
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: SwitchListTile(
                    secondary: const Icon(Icons.fingerprint),
                    title: const Text('Connexion biométrique'),
                    subtitle: Text(
                      _compatible
                          ? 'Utilisez votre empreinte ou Face ID pour déverrouiller MyNkap.'
                          : "Aucune biométrie ou code disponible sur cet appareil.",
                    ),
                    value: _active,
                    onChanged: (_compatible && !_enCours) ? _basculer : null,
                  ),
                ),
                if (_erreur != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _erreur!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ],
              ],
            ),
    );
  }
}
