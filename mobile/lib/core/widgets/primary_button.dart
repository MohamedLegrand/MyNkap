import 'package:flutter/material.dart';

/// Bouton d'action principal, avec indicateur de chargement intégré —
/// évite de dupliquer le pattern "désactivé + spinner pendant l'appel API"
/// dans chaque écran (même besoin que les boutons de soumission des
/// modales côté frontend, ex: `isSubmitting && <Loader2 .../>`).
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        child: isLoading
            ? const SizedBox(
                height: 18,
                width: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  valueColor: AlwaysStoppedAnimation(Colors.white),
                ),
              )
            : Text(label),
      ),
    );
  }
}
