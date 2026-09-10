# Tests d'intégration — parcours de bout en bout traversant plusieurs
# modules (auth, plans, comptes, transactions, budgets, dettes, épargne,
# analyse, jarvis...), par opposition aux tests unitaires par module dans
# tests/ (un fichier = un module). Réutilise les fixtures de tests/conftest.py
# (client, db_session...) — pytest les découvre automatiquement dans ce
# sous-dossier, aucun conftest.py dédié n'est nécessaire.
