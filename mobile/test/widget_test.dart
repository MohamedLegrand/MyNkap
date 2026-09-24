// Test de fumée : l'app démarre, et selon l'état de session (fourni ici
// par un faux AuthController — jamais le vrai, qui dépend de
// flutter_secure_storage et d'un appel réseau réel, voir
// AuthController.build) affiche le bon écran de départ. Prouve que
// ProviderScope, GoRouter et le thème s'assemblent sans erreur.
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mynkap_mobile/app.dart';
import 'package:mynkap_mobile/features/auth/domain/client.dart';
import 'package:mynkap_mobile/features/auth/presentation/controllers/app_lock_controller.dart';
import 'package:mynkap_mobile/features/auth/presentation/controllers/auth_controller.dart';

class _FakeAuthController extends AuthController {
  _FakeAuthController(this._etatInitial);

  final Client? _etatInitial;

  @override
  Future<Client?> build() async => _etatInitial;
}

class _FakeAppLockController extends AppLockController {
  _FakeAppLockController(this._etatInitial);

  final bool _etatInitial;

  @override
  bool build() => _etatInitial;
}

final _client = Client(
  idClient: 1,
  email: 'client@example.com',
  firstName: 'Awa',
  lastName: 'Biya',
  phone: '+237600000000',
  estActif: true,
  statutCompte: 'ACTIF',
  dateCreation: DateTime(2026, 1, 1),
);

void main() {
  // La 3e configuration (verrou biométrique) construit le vrai
  // authRepositoryProvider (BiometricLockScreen tente un déverrouillage dès
  // son affichage) — dotenv.env est donc lu, même si l'appel réseau/capteur
  // lui-même échoue proprement (MissingPluginException, capturée par
  // BiometricService.authentifier) dans cet environnement de test.
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000/api/v1');
  });

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

  testWidgets('affiche le tableau de bord quand la session est active et déverrouillée',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith(() => _FakeAuthController(_client)),
        ],
        child: const MyNkapApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Bonjour, Awa'), findsOneWidget);
  });

  testWidgets(
      "affiche l'écran de verrouillage biométrique quand la session est active mais verrouillée",
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authControllerProvider.overrideWith(() => _FakeAuthController(_client)),
          appLockProvider.overrideWith(() => _FakeAppLockController(false)),
        ],
        child: const MyNkapApp(),
      ),
    );
    // Quelques frames explicites, jamais pumpAndSettle() : l'écran tente un
    // déverrouillage biométrique dès son affichage (voir
    // BiometricLockScreen.initState), qui reste indéfiniment en attente
    // dans cet environnement de test (aucun canal de plateforme réel) —
    // seul le premier rendu nous intéresse ici, pour vérifier que le
    // routeur a bien choisi cet écran une fois la session résolue.
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    expect(find.text('MyNkap est verrouillé'), findsOneWidget);
    expect(find.text('Bonjour, Awa'), findsNothing);
  });

  test("AppLockController : verrouiller() puis deverrouiller() changent bien l'état", () {
    final conteneur = ProviderContainer();
    addTearDown(conteneur.dispose);

    expect(conteneur.read(appLockProvider), isTrue);
    conteneur.read(appLockProvider.notifier).verrouiller();
    expect(conteneur.read(appLockProvider), isFalse);
    conteneur.read(appLockProvider.notifier).deverrouiller();
    expect(conteneur.read(appLockProvider), isTrue);
  });
}
