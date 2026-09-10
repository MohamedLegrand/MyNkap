# Tests unitaires — une fonction/méthode pure isolée, sans base de données
# ni client HTTP (donc sans les fixtures `client`/`db_session` de
# tests/conftest.py) : construction d'objets en mémoire, assertions sur le
# résultat. Rapides et déterministes, par opposition à tests/ (comportement
# d'un module via l'API) et tests/integration/ (parcours traversant
# plusieurs modules). Un candidat idéal ici : un calcul ou une date qui ne
# dépend d'aucune requête (voir Dette.get_montant_restant,
# analyse.service._limites_mois, tontines.service._avancer_date...).
