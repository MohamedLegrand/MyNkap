import 'package:flutter/material.dart';

/// Affiché pendant la restauration de session au démarrage (voir
/// AuthController.build) — le routeur redirige automatiquement vers
/// /home ou /login dès que l'état est connu, cet écran ne navigue jamais
/// lui-même.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'MyNkap',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900),
            ),
            SizedBox(height: 20),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
