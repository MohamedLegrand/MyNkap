import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/router/app_routes.dart';
import '../../../auth/presentation/controllers/auth_controller.dart';

/// Coquille du tableau de bord — un point d'arrivée réel et protégé après
/// connexion, pour que le routeur et le flux d'auth soient vérifiables de
/// bout en bout. Les sections listées ci-dessous sont les prochaines
/// verticales à construire (une feature par domaine, voir
/// `features/<nom>/`), dans le même ordre que `DashboardLayout.tsx` côté
/// frontend.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  static const _sections = <_Section>[
    _Section('Comptes', Icons.account_balance_wallet_outlined),
    _Section('Transactions', Icons.receipt_long_outlined),
    _Section('Budgets', Icons.pie_chart_outline),
    _Section('Épargne', Icons.savings_outlined),
    _Section('Dettes', Icons.handshake_outlined),
    _Section('JARVIS', Icons.smart_toy_outlined),
    _Section('Analyse', Icons.show_chart),
    _Section('Récurrences', Icons.repeat),
    _Section('Rapports', Icons.description_outlined),
    _Section('Abonnement', Icons.workspace_premium_outlined),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final client = ref.watch(authControllerProvider).value;

    return Scaffold(
      appBar: AppBar(
        title: Text(client == null ? 'MyNkap' : 'Bonjour, ${client.firstName}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.fingerprint),
            tooltip: 'Sécurité',
            onPressed: () => context.push(AppRoutes.security),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Se déconnecter',
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.3,
        ),
        itemCount: _sections.length,
        itemBuilder: (context, index) {
          final section = _sections[index];
          return Card(
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('${section.titre} — à venir')),
                );
              },
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Icon(section.icone, size: 28, color: Theme.of(context).colorScheme.primary),
                    const SizedBox(height: 10),
                    Text(section.titre, style: const TextStyle(fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _Section {
  const _Section(this.titre, this.icone);

  final String titre;
  final IconData icone;
}
