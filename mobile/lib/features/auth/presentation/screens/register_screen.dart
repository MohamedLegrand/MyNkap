import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/router/app_routes.dart';
import '../../../../core/widgets/error_banner.dart';
import '../../../../core/widgets/primary_button.dart';
import '../../data/auth_repository.dart';

/// Ne passe pas par AuthController : l'inscription ne crée aucune session
/// (voir backend, POST /auth/register renvoie `otp_requis`, jamais de
/// jeton) — état de chargement/erreur purement local à cet écran.
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _prenomController = TextEditingController();
  final _nomController = TextEditingController();
  final _emailController = TextEditingController();
  final _telephoneController = TextEditingController();
  final _motDePasseController = TextEditingController();

  bool _isLoading = false;
  String? _erreur;

  @override
  void dispose() {
    _prenomController.dispose();
    _nomController.dispose();
    _emailController.dispose();
    _telephoneController.dispose();
    _motDePasseController.dispose();
    super.dispose();
  }

  Future<void> _sInscrire() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isLoading = true;
      _erreur = null;
    });

    final email = _emailController.text.trim();
    try {
      await ref.read(authRepositoryProvider).register(
            email: email,
            motDePasse: _motDePasseController.text,
            firstName: _prenomController.text.trim(),
            lastName: _nomController.text.trim(),
            phone: _telephoneController.text.trim(),
          );
      if (!mounted) return;
      context.push(AppRoutes.verifyOtp, extra: email);
    } catch (erreur) {
      setState(() {
        _erreur = erreur is ApiException ? erreur.message : 'Inscription impossible.';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Créer un compte')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_erreur != null) ...[
                  ErrorBanner(message: _erreur!),
                  const SizedBox(height: 16),
                ],
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _prenomController,
                        decoration: const InputDecoration(labelText: 'Prénom'),
                        validator: (v) => (v == null || v.isEmpty) ? 'Requis' : null,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _nomController,
                        decoration: const InputDecoration(labelText: 'Nom'),
                        validator: (v) => (v == null || v.isEmpty) ? 'Requis' : null,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'E-mail'),
                  validator: (v) => (v == null || !v.contains('@')) ? 'E-mail invalide.' : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _telephoneController,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Téléphone'),
                  validator: (v) => (v == null || v.isEmpty) ? 'Requis' : null,
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _motDePasseController,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Mot de passe'),
                  validator: (v) =>
                      (v == null || v.length < 8) ? '8 caractères minimum.' : null,
                ),
                const SizedBox(height: 24),
                PrimaryButton(
                  label: 'Créer mon compte',
                  isLoading: _isLoading,
                  onPressed: _sInscrire,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
