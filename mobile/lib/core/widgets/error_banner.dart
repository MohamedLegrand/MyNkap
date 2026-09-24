import 'package:flutter/material.dart';

/// Bandeau d'erreur générique — même rôle que
/// `{error && <p className="text-destructive">{error}</p>}`, répété dans
/// presque tous les formulaires du frontend.
class ErrorBanner extends StatelessWidget {
  const ErrorBanner({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final destructive = Theme.of(context).colorScheme.error;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: destructive.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: destructive.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, size: 18, color: destructive),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: destructive, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}
