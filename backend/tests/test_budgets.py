from decimal import Decimal
import pytest
from app.modules.budgets.models import Budget, Categorie
from app.modules.audit.models import AuditLog
from tests.conftest import se_connecter

def _register_and_login(client, email="budgets.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Budget",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

def _creer_compte(client, headers, solde_initial=100000, nom="Compte principal"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()

def test_crud_categorie(client):
    headers = _register_and_login(client, "cat.test@example.com")
    nombre_avant = len(client.get("/api/v1/categories", headers=headers).json())

    # 1. Création de catégorie
    response = client.post(
        "/api/v1/categories",
        json={"nom": "Abonnements", "type": "DEPENSE", "icone": "utensils", "couleur": "#F97316"},
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nom"] == "Abonnements"
    assert data["type"] == "DEPENSE"
    assert data["est_actif"] is True

    # Doublon impossible
    response_dup = client.post(
        "/api/v1/categories",
        json={"nom": "Abonnements", "type": "DEPENSE"},
        headers=headers
    )
    assert response_dup.status_code == 400

    # 2. Lister les catégories : les catégories par défaut créées à
    # l'inscription (voir CATEGORIES_PAR_DEFAUT) + celle qu'on vient d'ajouter
    response_list = client.get("/api/v1/categories", headers=headers)
    assert response_list.status_code == 200
    assert len(response_list.json()) == nombre_avant + 1


def test_categories_par_defaut_a_linscription(client):
    headers = _register_and_login(client, "cat.defaut@example.com")
    categories = client.get("/api/v1/categories", headers=headers).json()

    noms = {c["nom"] for c in categories}
    assert "Alimentation" in noms
    assert "Salaire" in noms
    assert all(c["est_actif"] for c in categories)
    # Utilisable immédiatement pour une transaction, sans création manuelle
    assert len(categories) > 0


def test_modifier_categorie(client):
    headers = _register_and_login(client, "cat.modifier@example.com")
    categorie = client.post(
        "/api/v1/categories", json={"nom": "Sport", "type": "DEPENSE"}, headers=headers
    ).json()

    modifiee = client.put(
        f"/api/v1/categories/{categorie['id_categorie']}",
        json={"nom": "Sport & Fitness", "couleur": "#84CC16"},
        headers=headers,
    )
    assert modifiee.status_code == 200
    assert modifiee.json()["nom"] == "Sport & Fitness"
    assert modifiee.json()["couleur"] == "#84CC16"

    # Renommer vers un nom déjà pris (même type) est refusé
    conflit = client.put(
        f"/api/v1/categories/{categorie['id_categorie']}",
        json={"nom": "Alimentation"},
        headers=headers,
    )
    assert conflit.status_code == 400


def test_icone_et_couleur_de_categorie_limitees_a_une_liste_blanche(client):
    """
    icone/couleur ne sont pas du texte libre : seules les valeurs du
    catalogue fermé (voir budgets.schemas.ICONES_CATEGORIE/COULEURS_CATEGORIE)
    sont acceptées, pour empêcher qu'un client n'y injecte une valeur
    arbitraire (nom de composant, chemin, code CSS/HTML...).
    """
    headers = _register_and_login(client, "cat.icone.securite@example.com")

    # Icône hors catalogue -> 422
    res_icone = client.post(
        "/api/v1/categories",
        json={"nom": "Test Sécu", "type": "DEPENSE", "icone": "<script>alert(1)</script>"},
        headers=headers,
    )
    assert res_icone.status_code == 422

    # Couleur hors catalogue -> 422
    res_couleur = client.post(
        "/api/v1/categories",
        json={"nom": "Test Sécu 2", "type": "DEPENSE", "couleur": "javascript:alert(1)"},
        headers=headers,
    )
    assert res_couleur.status_code == 422

    # Une valeur du catalogue reste acceptée
    res_ok = client.post(
        "/api/v1/categories",
        json={"nom": "Test Sécu 3", "type": "DEPENSE", "icone": "sparkles", "couleur": "#254E2A"},
        headers=headers,
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["icone"] == "sparkles"
    assert res_ok.json()["couleur"] == "#254E2A"


def test_desactiver_categorie_bloque_son_usage_futur_mais_pas_lhistorique(client):
    headers = _register_and_login(client, "cat.softdelete@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    categorie = client.post(
        "/api/v1/categories", json={"nom": "Café", "type": "DEPENSE"}, headers=headers
    ).json()

    depense = client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 1000,
            "type": "DEPENSE",
        },
        headers=headers,
    )
    assert depense.status_code == 201

    desactivation = client.delete(f"/api/v1/categories/{categorie['id_categorie']}", headers=headers)
    assert desactivation.status_code == 204

    # Absente de la liste par défaut, toujours consultable par ID
    liste = client.get("/api/v1/categories", headers=headers).json()
    assert categorie["id_categorie"] not in [c["id_categorie"] for c in liste]
    toujours_la = client.get(f"/api/v1/categories/{categorie['id_categorie']}", headers=headers)
    assert toujours_la.status_code == 200
    assert toujours_la.json()["est_actif"] is False

    # Impossible de créer une nouvelle transaction ou un budget dessus
    nouvelle_depense = client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 500,
            "type": "DEPENSE",
        },
        headers=headers,
    )
    assert nouvelle_depense.status_code == 404

    nouveau_budget = client.post(
        "/api/v1/budgets",
        json={"id_categorie": categorie["id_categorie"], "montant_limite": 5000, "mois": 9, "annee": 2026},
        headers=headers,
    )
    assert nouveau_budget.status_code == 404

    reactivation = client.post(f"/api/v1/categories/{categorie['id_categorie']}/reactiver", headers=headers)
    assert reactivation.status_code == 200
    assert reactivation.json()["est_actif"] is True

def test_creation_budget_contraintes(client, db_session):
    headers = _register_and_login(client, "budget.constraint@example.com")
    
    # Création des catégories
    cat_depense = client.post(
        "/api/v1/categories",
        json={"nom": "Divertissement", "type": "DEPENSE"},
        headers=headers
    ).json()
    
    cat_revenu = client.post(
        "/api/v1/categories",
        json={"nom": "Investissements", "type": "REVENU"},
        headers=headers
    ).json()

    # 1. Budget sur catégorie de REVENU interdit
    response_rev = client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": cat_revenu["id_categorie"],
            "montant_limite": 50000,
            "mois": 7,
            "annee": 2026
        },
        headers=headers
    )
    assert response_rev.status_code == 400
    assert "DEPENSE" in response_rev.json()["detail"]

    # 2. Budget valide sur catégorie de DEPENSE
    response_ok = client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": cat_depense["id_categorie"],
            "montant_limite": 30000,
            "mois": 7,
            "annee": 2026
        },
        headers=headers
    )
    assert response_ok.status_code == 201
    budget_data = response_ok.json()
    assert budget_data["montant_limite"] == "30000.00"
    assert budget_data["mois"] == 7
    assert budget_data["annee"] == 2026

    # 3. Doublon pour le même mois/annee/categorie interdit (triplet unique)
    response_dup = client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": cat_depense["id_categorie"],
            "montant_limite": 40000,
            "mois": 7,
            "annee": 2026
        },
        headers=headers
    )
    assert response_dup.status_code == 400

def test_calcul_dynamique_et_alertes(client, db_session):
    headers = _register_and_login(client, "budget.alert@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    
    cat_transport = client.post(
        "/api/v1/categories",
        json={"nom": "Déplacements", "type": "DEPENSE"},
        headers=headers
    ).json()

    # 1. Créer un budget de 10 000 XAF pour Juillet 2026
    budget = client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": cat_transport["id_categorie"],
            "montant_limite": 10000,
            "mois": 7,
            "annee": 2026
        },
        headers=headers
    ).json()

    # Vérification initiale : dépenses = 0, alertes = False
    assert budget["montant_depense"] == "0.00"
    assert budget["montant_restant"] == "10000.00"
    assert budget["pourcentage_utilise"] == 0.0
    assert not budget["alerte_80"]
    assert not budget["alerte_100"]

    # 2. Créer une transaction DEPENSE de 5 000 XAF (50% d'utilisation) le 24 Juillet 2026
    tx_res = client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": cat_transport["id_categorie"],
            "montant": 5000,
            "type": "DEPENSE",
            "date": "2026-07-24",
            "description": "Essence taxi"
        },
        headers=headers
    )
    assert tx_res.status_code == 201

    # Lire le budget -> Dépenses = 5000 XAF, pas d'alertes
    budget_read = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers).json()
    assert budget_read["montant_depense"] == "5000.00"
    assert budget_read["montant_restant"] == "5000.00"
    assert budget_read["pourcentage_utilise"] == 50.0
    assert not budget_read["alerte_80"]

    # 3. Créer une deuxième dépense de 3 500 XAF (Porte le total à 8 500 XAF, soit 85% d'utilisation)
    client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": cat_transport["id_categorie"],
            "montant": 3500,
            "type": "DEPENSE",
            "date": "2026-07-24",
            "description": "Taxi Douala"
        },
        headers=headers
    )

    # Lire le budget -> Doit déclencher l'alerte 80%
    budget_read2 = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers).json()
    assert budget_read2["montant_depense"] == "8500.00"
    assert budget_read2["pourcentage_utilise"] == 85.0
    assert budget_read2["alerte_80"]
    assert not budget_read2["alerte_100"]

    # Vérifier l'AuditLog pour ALERTE_BUDGET_80
    logs_80 = db_session.query(AuditLog).filter(
        AuditLog.action == "ALERTE_BUDGET_80",
        AuditLog.id_ressource == budget["id_budget"]
    ).all()
    assert len(logs_80) == 1

    # 4. Créer une troisième dépense de 2 000 XAF (Porte le total à 10 500 XAF, soit 105% d'utilisation)
    client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": cat_transport["id_categorie"],
            "montant": 2000,
            "type": "DEPENSE",
            "date": "2026-07-24",
            "description": "Bus Yaoundé"
        },
        headers=headers
    )

    # Lire le budget -> Doit déclencher l'alerte 100% (dépassé)
    budget_read3 = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers).json()
    assert budget_read3["montant_depense"] == "10500.00"
    assert budget_read3["pourcentage_utilise"] == 105.0
    assert budget_read3["alerte_100"]
    assert budget_read3["est_depasse"]

    # Vérifier l'AuditLog pour ALERTE_BUDGET_100
    logs_100 = db_session.query(AuditLog).filter(
        AuditLog.action == "ALERTE_BUDGET_100",
        AuditLog.id_ressource == budget["id_budget"]
    ).all()
    assert len(logs_100) == 1


def test_annuler_une_depense_reduit_le_montant_depense_du_budget(client):
    # Une dépense annulée ne doit plus compter dans le budget, exactement
    # comme elle ne compte plus dans le solde du compte.
    headers = _register_and_login(client, "budget.annulation@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)

    categorie = client.post(
        "/api/v1/categories", json={"nom": "Divers", "type": "DEPENSE"}, headers=headers
    ).json()
    budget = client.post(
        "/api/v1/budgets",
        json={"id_categorie": categorie["id_categorie"], "montant_limite": 10000, "mois": 7, "annee": 2026},
        headers=headers,
    ).json()

    depense = client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 5000,
            "type": "DEPENSE",
            "date": "2026-07-24",
        },
        headers=headers,
    ).json()

    avant = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers).json()
    assert avant["montant_depense"] == "5000.00"

    annulation = client.post(f"/api/v1/transactions/{depense['id_transaction']}/annuler", headers=headers)
    assert annulation.status_code == 201

    apres = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers).json()
    assert apres["montant_depense"] == "0.00"
    assert apres["montant_restant"] == "10000.00"


def test_budget_introuvable_renvoie_404_pas_400(client):
    headers = _register_and_login(client, "budget.404@example.com")

    obtenir = client.get("/api/v1/budgets/999999", headers=headers)
    assert obtenir.status_code == 404

    modifier = client.put("/api/v1/budgets/999999", json={"montant_limite": 1000}, headers=headers)
    assert modifier.status_code == 404

    supprimer = client.delete("/api/v1/budgets/999999", headers=headers)
    assert supprimer.status_code == 404


def test_desactiver_budget_est_une_desactivation_logique(client):
    headers = _register_and_login(client, "budget.softdelete@example.com")
    categorie = client.post(
        "/api/v1/categories", json={"nom": "Médical", "type": "DEPENSE"}, headers=headers
    ).json()
    budget = client.post(
        "/api/v1/budgets",
        json={"id_categorie": categorie["id_categorie"], "montant_limite": 5000, "mois": 8, "annee": 2026},
        headers=headers,
    ).json()

    desactivation = client.delete(f"/api/v1/budgets/{budget['id_budget']}", headers=headers)
    assert desactivation.status_code == 204

    # Toujours consultable directement par ID (jamais supprimé réellement)
    toujours_la = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers)
    assert toujours_la.status_code == 200
    assert toujours_la.json()["est_actif"] is False

    # Absent de la liste par défaut, présent avec include_inactifs
    liste_defaut = client.get("/api/v1/budgets", headers=headers).json()
    assert len(liste_defaut) == 0
    liste_complete = client.get("/api/v1/budgets?include_inactifs=true", headers=headers).json()
    assert len(liste_complete) == 1

    reactivation = client.post(f"/api/v1/budgets/{budget['id_budget']}/reactiver", headers=headers)
    assert reactivation.status_code == 200
    assert reactivation.json()["est_actif"] is True


def test_modifier_montant_limite_reinitialise_les_flags_dalerte(client):
    headers = _register_and_login(client, "budget.resetflags@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    categorie = client.post(
        "/api/v1/categories", json={"nom": "Restaurant", "type": "DEPENSE"}, headers=headers
    ).json()
    budget = client.post(
        "/api/v1/budgets",
        json={"id_categorie": categorie["id_categorie"], "montant_limite": 1000, "mois": 7, "annee": 2026},
        headers=headers,
    ).json()

    # Dépasse immédiatement 100%
    client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 1500,
            "type": "DEPENSE",
            "date": "2026-07-24",
        },
        headers=headers,
    )
    apres_depense = client.get(f"/api/v1/budgets/{budget['id_budget']}", headers=headers).json()
    assert apres_depense["alerte_100"] is True

    # Le client relève sa limite très au-dessus de ce qui est dépensé
    modifie = client.put(
        f"/api/v1/budgets/{budget['id_budget']}", json={"montant_limite": 100000}, headers=headers
    )
    assert modifie.status_code == 200
    assert modifie.json()["alerte_100"] is False
    assert modifie.json()["alerte_80"] is False
    assert modifie.json()["pourcentage_utilise"] == 1.5
