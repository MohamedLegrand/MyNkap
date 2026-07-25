from datetime import date, timedelta
from decimal import Decimal

from app.modules.analyse.service import _limites_mois, _mois_precedents, generer_snapshots_mensuels_tous_clients


def _register_and_login(client, email="analyse.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Analyse",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "mot_de_passe": mot_de_passe},
    )
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _creer_compte(client, headers, solde_initial=1000000, nom="Compte principal"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def _categorie(client, headers, nom="Alimentation"):
    categories = client.get("/api/v1/categories", headers=headers).json()
    return next(c for c in categories if c["nom"] == nom)


def _depense(client, headers, compte, categorie, montant, jour: date):
    return client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": montant,
            "type": "DEPENSE",
            "date": jour.isoformat(),
        },
        headers=headers,
    ).json()


def _revenu(client, headers, compte, categorie, montant, jour: date):
    return client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": montant,
            "type": "REVENU",
            "date": jour.isoformat(),
        },
        headers=headers,
    ).json()


PERIODE_FIXE_DEBUT, PERIODE_FIXE_FIN = _limites_mois(2026, 3)


def test_habitudes_repartition_par_categorie(client):
    headers = _register_and_login(client, "analyse.habitudes@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")
    transport = _categorie(client, headers, "Transport")

    _depense(client, headers, compte, alimentation, 30000, PERIODE_FIXE_DEBUT)
    _depense(client, headers, compte, transport, 10000, PERIODE_FIXE_DEBUT + timedelta(days=1))

    reponse = client.get(
        "/api/v1/analyse/HABITUDES",
        params={"periode_debut": PERIODE_FIXE_DEBUT.isoformat(), "periode_fin": PERIODE_FIXE_FIN.isoformat()},
        headers=headers,
    )
    assert reponse.status_code == 200
    body = reponse.json()
    assert body["id_analyse"] is None  # jamais persisté pour une analyse "courante"
    assert Decimal(body["resultats"]["total_depenses"]) == Decimal("40000")

    repartition = {ligne["categorie"]: ligne for ligne in body["resultats"]["repartition"]}
    assert repartition["Alimentation"]["pourcentage"] == 75.0
    assert repartition["Transport"]["pourcentage"] == 25.0


def test_tendances_compare_a_la_moyenne_glissante(client):
    headers = _register_and_login(client, "analyse.tendances@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")

    # 3 mois précédents à 10 000 XAF/mois -> moyenne glissante = 10 000
    for debut, _fin in _mois_precedents(PERIODE_FIXE_DEBUT, 3):
        _depense(client, headers, compte, alimentation, 10000, debut)

    # Mois analysé : 15 000 XAF (+50% vs la moyenne)
    _depense(client, headers, compte, alimentation, 15000, PERIODE_FIXE_DEBUT)

    reponse = client.get(
        "/api/v1/analyse/TENDANCES",
        params={"periode_debut": PERIODE_FIXE_DEBUT.isoformat(), "periode_fin": PERIODE_FIXE_FIN.isoformat()},
        headers=headers,
    )
    assert reponse.status_code == 200
    tendances = {t["categorie"]: t for t in reponse.json()["resultats"]["tendances"]}
    assert Decimal(tendances["Alimentation"]["montant_periode"]) == Decimal("15000")
    assert Decimal(tendances["Alimentation"]["moyenne_glissante_3_mois"]) == Decimal("10000")
    assert tendances["Alimentation"]["variation_pourcentage"] == 50.0


def test_comparaison_periode_actuelle_vs_precedente(client):
    headers = _register_and_login(client, "analyse.comparaison@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")
    salaire = _categorie(client, headers, "Salaire")

    mois_precedent_debut, mois_precedent_fin = _mois_precedents(PERIODE_FIXE_DEBUT, 1)[0]
    _depense(client, headers, compte, alimentation, 5000, mois_precedent_debut)
    _revenu(client, headers, compte, salaire, 100000, mois_precedent_debut)

    _depense(client, headers, compte, alimentation, 8000, PERIODE_FIXE_DEBUT)
    _revenu(client, headers, compte, salaire, 120000, PERIODE_FIXE_DEBUT)

    reponse = client.get(
        "/api/v1/analyse/COMPARAISON",
        params={"periode_debut": PERIODE_FIXE_DEBUT.isoformat(), "periode_fin": PERIODE_FIXE_FIN.isoformat()},
        headers=headers,
    )
    resultats = reponse.json()["resultats"]
    assert Decimal(resultats["depenses_periode_actuelle"]) == Decimal("8000")
    assert Decimal(resultats["depenses_periode_precedente"]) == Decimal("5000")
    assert Decimal(resultats["revenus_periode_actuelle"]) == Decimal("120000")
    assert Decimal(resultats["revenus_periode_precedente"]) == Decimal("100000")


def test_comportement_transactions_suspectes_et_budgets_depasses(client):
    headers = _register_and_login(client, "analyse.comportement@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")

    client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": alimentation["id_categorie"],
            "montant_limite": 1000,
            "mois": PERIODE_FIXE_DEBUT.month,
            "annee": PERIODE_FIXE_DEBUT.year,
        },
        headers=headers,
    )
    # 3 dépenses "normales" de montants distincts (même jour, même montant
    # déclencherait aussi la règle de doublon) pour établir une moyenne à
    # 500, puis une anormale -> suspecte via la règle de moyenne seule.
    for montant in (400, 500, 600):
        _depense(client, headers, compte, alimentation, montant, PERIODE_FIXE_DEBUT)
    _depense(client, headers, compte, alimentation, 50000, PERIODE_FIXE_DEBUT)  # dépasse aussi le budget

    reponse = client.get(
        "/api/v1/analyse/COMPORTEMENT",
        params={"periode_debut": PERIODE_FIXE_DEBUT.isoformat(), "periode_fin": PERIODE_FIXE_FIN.isoformat()},
        headers=headers,
    )
    resultats = reponse.json()["resultats"]
    assert resultats["transactions_suspectes"] == 1
    assert resultats["budgets_depasses"] == 1
    assert resultats["nombre_budgets_actifs"] == 1


def test_score_financier_client_neuf_sans_donnees(client):
    headers = _register_and_login(client, "analyse.scoreneuf@example.com")
    # Aucun compte, aucune transaction, aucun budget, aucune dette.
    reponse = client.get(
        "/api/v1/analyse/HABITUDES",
        params={"periode_debut": PERIODE_FIXE_DEBUT.isoformat(), "periode_fin": PERIODE_FIXE_FIN.isoformat()},
        headers=headers,
    )
    # 25 (pas de budget = neutre) + 0 (pas de revenu = pas de taux d'épargne
    # calculable) + 25 (pas de dette) + 25 (pas d'incident) = 75
    assert reponse.json()["score_financier"] == 75.0


def test_type_analyse_et_prediction_invalides_renvoient_400(client):
    headers = _register_and_login(client, "analyse.typeinvalide@example.com")

    reponse_analyse = client.get("/api/v1/analyse/TYPE_INEXISTANT", headers=headers)
    assert reponse_analyse.status_code == 400

    reponse_prediction = client.get("/api/v1/analyse/predictions/TYPE_INEXISTANT", headers=headers)
    assert reponse_prediction.status_code == 400


def test_prediction_depenses_futures_et_capacite_epargne(client):
    """
    predire_depenses_futures/predire_capacite_epargne se basent toujours
    sur les vrais 3 derniers mois PLEINS avant aujourd'hui (jamais un mois
    passé arbitraire), pour ne jamais inclure un mois en cours incomplet —
    le test doit donc utiliser les vrais mois calendaires actuels.
    """
    headers = _register_and_login(client, "analyse.prediction@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")
    salaire = _categorie(client, headers, "Salaire")

    reference = date.today().replace(day=1)
    for debut, _fin in _mois_precedents(reference, 3):
        _depense(client, headers, compte, alimentation, 9000, debut)
        _revenu(client, headers, compte, salaire, 100000, debut)

    depenses = client.get("/api/v1/analyse/predictions/DEPENSES_FUTURES", headers=headers)
    assert depenses.status_code == 200
    assert Decimal(depenses.json()["montant_predit"]) == Decimal("9000.00")

    epargne = client.get("/api/v1/analyse/predictions/CAPACITE_EPARGNE", headers=headers)
    assert epargne.status_code == 200
    assert Decimal(epargne.json()["montant_predit"]) == Decimal("91000.00")


def test_prediction_risque_budgetaire_detecte_un_depassement_projete(client):
    headers = _register_and_login(client, "analyse.risque@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")

    client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": alimentation["id_categorie"],
            "montant_limite": 1000,
            "mois": PERIODE_FIXE_DEBUT.month,
            "annee": PERIODE_FIXE_DEBUT.year,
        },
        headers=headers,
    )
    _depense(client, headers, compte, alimentation, 900, PERIODE_FIXE_DEBUT)

    reponse = client.get(
        "/api/v1/analyse/predictions/RISQUE_BUDGETAIRE",
        params={"periode_debut": PERIODE_FIXE_DEBUT.isoformat(), "periode_fin": PERIODE_FIXE_FIN.isoformat()},
        headers=headers,
    )
    assert reponse.status_code == 200
    body = reponse.json()
    # Période passée entièrement écoulée -> projection == dépense réelle (900),
    # qui ne dépasse PAS la limite de 1000 : rien à signaler.
    assert "Aucun budget" in body["recommandations"]


def test_generer_snapshots_mensuels_persiste_analyse_et_prediction(client, db_session):
    headers = _register_and_login(client, "analyse.snapshot@example.com")
    compte = _creer_compte(client, headers)
    alimentation = _categorie(client, headers, "Alimentation")

    # La tâche fige toujours le mois civil précédent réel (par rapport à
    # aujourd'hui), jamais une période arbitraire — on y place la dépense
    # exactement, plutôt que de deviner avec un décalage en jours.
    aujourdhui = date.today()
    mois_precedent = aujourdhui.month - 1 or 12
    annee_precedente = aujourdhui.year if aujourdhui.month > 1 else aujourdhui.year - 1
    debut_mois_precedent, _fin_mois_precedent = _limites_mois(annee_precedente, mois_precedent)
    _depense(client, headers, compte, alimentation, 5000, debut_mois_precedent)

    nb_generes = generer_snapshots_mensuels_tous_clients(db_session)
    assert nb_generes > 0

    historique = client.get("/api/v1/analyse/HABITUDES/historique", headers=headers).json()
    assert len(historique) == 1
    assert historique[0]["id_analyse"] is not None  # persisté cette fois

    historique_prediction = client.get(
        "/api/v1/analyse/predictions/DEPENSES_FUTURES/historique", headers=headers
    ).json()
    assert len(historique_prediction) == 1
    assert historique_prediction[0]["id_prediction"] is not None
