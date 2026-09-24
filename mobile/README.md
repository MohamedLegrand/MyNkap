# MyNkap Mobile

Application mobile (Flutter/Dart, Android + iOS) de MyNkap, la plateforme
SaaS de gestion de finances personnelles. Consomme la même API REST que
`frontend/` (voir `backend/`) — aucune logique métier ici, tout le calcul
financier (immuabilité, atomicité, plafonds de budget...) reste côté
serveur.

## Démarrer

```
cp .env.example .env   # renseigner API_BASE_URL (voir commentaires du fichier)
flutter pub get
flutter run
```

## Architecture

Organisation par fonctionnalité (`features/`), pas par type de fichier —
un dossier par domaine métier, le même découpage que les modules du
backend (`backend/app/modules/*`) et les sections du frontend
(`frontend/src/components`, `frontend/src/pages`), pour qu'un même concept
se retrouve au même endroit dans les trois projets.

```
lib/
  main.dart                 Point d'entrée : charge .env, lance MyNkapApp
  app.dart                  MaterialApp.router (thème + routage)
  core/                     Rien de spécifique à un domaine métier
    config/env.dart         Lecture de .env
    theme/                  Palette et ThemeData (clair/sombre)
    network/                Client Dio, intercepteur d'auth, exceptions
    storage/                Jetons de session (flutter_secure_storage)
    router/                 go_router + garde d'authentification
    constants/              Chemins de l'API (miroir des routeurs FastAPI)
    widgets/                Composants réutilisables (bouton, bandeau d'erreur...)
  features/
    auth/                   Inscription, OTP, connexion, mot de passe oublié
    dashboard/               Coquille du tableau de bord (accueil post-connexion)
    comptes/ transactions/ budgets/ dettes/ epargne/
    jarvis/ analyse/ plans/ rapports/ notifications/ settings/
                             Une verticale par domaine, à construire au fur
                             et à mesure (dossiers déjà posés, voir ci-dessous)
```

Chaque feature suit la même sous-structure, quand elle est implémentée :

```
features/<nom>/
  data/            Appels HTTP bruts (*_api.dart) + orchestration (*_repository.dart)
  domain/          Modèles immuables, miroirs des schémas Pydantic du backend
  presentation/
    controllers/   État (Riverpod — AsyncNotifier le plus souvent)
    screens/       Écrans pleine page
    widgets/       Composants propres à cette feature
```

Seul `auth/` est entièrement construit pour l'instant (verticale de
référence, de bout en bout : appel API → stockage sécurisé → état
Riverpod → routage protégé). Les autres dossiers existent déjà mais sont
vides — à remplir en suivant exactement le même schéma.

### Choix techniques

- **État** : Riverpod (`flutter_riverpod`), sans génération de code pour
  rester simple à lire — `Provider` pour les dépendances (Dio, repositories),
  `AsyncNotifier` pour l'état asynchrone (session, listes de ressources...).
- **Réseau** : Dio, avec un intercepteur (`AuthInterceptor`) qui pose le
  jeton d'accès sur chaque requête et tente un seul rafraîchissement
  silencieux sur 401 avant d'abandonner — même logique que
  `frontend/src/services/api.ts`, adaptée au pattern `QueuedInterceptor` de
  Dio (un seul rafraîchissement même si plusieurs requêtes échouent en même
  temps).
- **Session** : jetons stockés via `flutter_secure_storage` (Keychain iOS /
  Keystore Android) — contrairement au web, qui les garde en
  `localStorage` faute de mieux dans un navigateur, un stockage chiffré
  natif est disponible ici et protège les jetons même si une faille
  applicative existait ailleurs dans l'app.
- **Routage** : `go_router`, avec une redirection centralisée qui observe
  l'état de session (voir `core/router/app_router.dart`) — jamais de garde
  dupliquée écran par écran.
- **Palette** : recopiée depuis `frontend/tailwind.config.js` et
  `frontend/src/index.css` (voir `core/theme/app_colors.dart`) — même
  identité visuelle que le web, aucune source commune entre les deux stacks
  pour l'instant (à reporter à la main si la palette change).

### Ce qui reste à faire

- Construire les autres features en suivant le modèle `auth/`.
- Internationalisation FR/EN (le web utilise `i18next` + `locales/fr.json`,
  `en.json` — l'équivalent Flutter est `flutter_localizations` + des
  fichiers `.arb`, pas encore mis en place ici : tous les textes sont pour
  l'instant en français, codés en dur).
- Icône et écran de démarrage natifs (`flutter_launcher_icons`,
  `flutter_native_splash`).
- Connexion Google (JARVIS vocal, notifications push...) : non couverts par
  cette première passe d'architecture.
