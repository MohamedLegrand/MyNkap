import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/router/app_routes.dart';
import '../../../../core/widgets/error_banner.dart';
import '../../../../core/widgets/primary_button.dart';
import '../controllers/auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.messageInitial});

  /// Message affiché à l'arrivée (ex: "compte vérifié, connectez-vous"
  /// après OtpScreen) — jamais une erreur, un simple message informatif.
  final String? messageInitial;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _motDePasseController = TextEditingController();
  bool _motDePasseVisible = false;

  @override
  void dispose() {
    _emailController.dispose();
    _motDePasseController.dispose();
    super.dispose();
  }

  Future<void> _seConnecter() async {
    if (!_formKey.currentState!.validate()) return;
    await ref.read(authControllerProvider.notifier).login(
          email: _emailController.text.trim(),
          motDePasse: _motDePasseController.text,
        );
    // La redirection vers /home, si la connexion réussit, est gérée par
    // AppRouter (il observe authControllerProvider) — rien à faire ici.
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final erreur = authState.hasError
        ? (authState.error is ApiException
            ? (authState.error as ApiException).message
            : 'Adresse e-mail ou mot de passe incorrect.')
        : null;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 40),
                const Text(
                  'MyNkap',
                  style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                Text(
                  'Connectez-vous à votre compte',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 32),
                if (widget.messageInitial != null) ...[
                  Text(
                    widget.messageInitial!,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 16),
                ],
                if (erreur != null) ...[
                  ErrorBanner(message: erreur),
                  const SizedBox(height: 16),
                ],
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'E-mail'),
                  validator: (valeur) =>
                      (valeur == null || !valeur.contains('@')) ? 'E-mail invalide.' : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _motDePasseController,
                  obscureText: !_motDePasseVisible,
                  decoration: InputDecoration(
                    labelText: 'Mot de passe',
                    suffixIcon: IconButton(
                      icon: Icon(_motDePasseVisible ? Icons.visibility_off : Icons.visibility),
                      onPressed: () => setState(() => _motDePasseVisible = !_motDePasseVisible),
                    ),
                  ),
                  validator: (valeur) =>
                      (valeur == null || valeur.isEmpty) ? 'Mot de passe requis.' : null,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => context.push(AppRoutes.forgotPassword),
                    child: const Text('Mot de passe oublié ?'),
                  ),
                ),
                const SizedBox(height: 12),
                PrimaryButton(
                  label: 'Se connecter',
                  isLoading: authState.isLoading,
                  onPressed: _seConnecter,
                ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text("Pas encore de compte ?"),
                    TextButton(
                      onPressed: () => context.push(AppRoutes.register),
                      child: const Text('Créer un compte'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
