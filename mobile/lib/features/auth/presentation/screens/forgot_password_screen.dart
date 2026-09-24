import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/widgets/primary_button.dart';
import '../../data/auth_repository.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _emailController = TextEditingController();
  bool _isLoading = false;
  bool _envoye = false;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _envoyer() async {
    final email = _emailController.text.trim();
    if (!email.contains('@')) return;

    setState(() => _isLoading = true);
    try {
      // Réponse toujours générique côté backend (jamais d'indication si
      // l'e-mail existe ou non) : rien à distinguer ici, seulement afficher
      // la confirmation dans tous les cas.
      await ref.read(authRepositoryProvider).forgotPassword(email);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _envoye = true;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mot de passe oublié')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_envoye)
                const Text(
                  "Si l'adresse existe, un e-mail de récupération vient d'être envoyé.",
                )
              else ...[
                const Text('Recevez un lien de réinitialisation par e-mail.'),
                const SizedBox(height: 16),
                TextField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'E-mail'),
                ),
                const SizedBox(height: 16),
                PrimaryButton(
                  label: 'Envoyer le lien',
                  isLoading: _isLoading,
                  onPressed: _envoyer,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
