import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/router/app_routes.dart';
import '../../../../core/widgets/error_banner.dart';
import '../../../../core/widgets/primary_button.dart';
import '../../data/auth_repository.dart';

class OtpScreen extends ConsumerStatefulWidget {
  const OtpScreen({super.key, required this.email});

  final String email;

  @override
  ConsumerState<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends ConsumerState<OtpScreen> {
  final _codeController = TextEditingController();
  bool _isLoading = false;
  String? _erreur;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _verifier() async {
    if (_codeController.text.trim().length != 6) {
      setState(() => _erreur = 'Le code contient 6 chiffres.');
      return;
    }
    setState(() {
      _isLoading = true;
      _erreur = null;
    });

    try {
      await ref.read(authRepositoryProvider).verifyOtp(
            email: widget.email,
            code: _codeController.text.trim(),
          );
      if (!mounted) return;
      context.go(
        AppRoutes.login,
        extra: 'Adresse e-mail vérifiée. Vous pouvez vous connecter.',
      );
    } catch (erreur) {
      setState(() {
        _erreur = erreur is ApiException ? erreur.message : 'Code invalide ou expiré.';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vérification')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Un code à 6 chiffres a été envoyé à ${widget.email}, valable 45 minutes.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 20),
              if (_erreur != null) ...[
                ErrorBanner(message: _erreur!),
                const SizedBox(height: 16),
              ],
              TextField(
                controller: _codeController,
                keyboardType: TextInputType.number,
                maxLength: 6,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 28, letterSpacing: 8, fontWeight: FontWeight.bold),
                decoration: const InputDecoration(counterText: ''),
              ),
              const SizedBox(height: 12),
              PrimaryButton(
                label: 'Vérifier',
                isLoading: _isLoading,
                onPressed: _verifier,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
