// Test de fumée : l'app démarre, et selon l'état de session (fourni ici
// par un faux AuthController — jamais le vrai, qui dépend de
// flutter_secure_storage et d'un appel réseau réel, voir
// AuthController.build) affiche le bon écran de départ. Prouve que
// ProviderScope, GoRouter et le thème s'assemblent sans erreur.
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mynkap_mobile/app.dart';
import 'package:mynkap_mobile/features/auth/domain/client.dart';
import 'package:mynkap_mobile/features/auth/presentation/controllers/auth_controller.dart';

class _FakeAuthController extends AuthController {
  _FakeAuthController(this._etatInitial);

  final Client? _etatInitial;

  @override
  Future<Client?> build() async => _etatInitial;
}

void main() {
  testWidgets('affiche l\'écran de connexion quand la session est absente', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith(() => _FakeAuthController(null)),
        ],
        child: const MyNkapApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('MyNkap'), findsWidgets);
    expect(find.text('Connectez-vous à votre compte'), findsOneWidget);
  });
}
