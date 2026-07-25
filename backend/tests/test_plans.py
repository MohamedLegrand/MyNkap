from datetime import datetime, timedelta

from app.modules.plans import service as plans_service
from app.modules.plans.models import Abonnement


def _register_and_login(client, email="plans.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Plan",
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


def test_lister_plans_est_public(client):
    # Aucun header d'authentification envoyé.
    reponse = client.get("/api/v1/plans")
    assert reponse.status_code == 200
    noms = {p["nom"] for p in reponse.json()}
    assert noms == {"GRATUIT", "ESSENTIEL", "PREMIUM"}


def test_nouveau_client_a_un_abonnement_gratuit_actif(client):
    headers = _register_and_login(client, "plans.nouveau@example.com")
    reponse = client.get("/api/v1/abonnement", headers=headers)
    assert reponse.status_code == 200
    body = reponse.json()
    assert body["plan"]["nom"] == "GRATUIT"
    assert body["statut"] == "ACTIF"
    assert body["date_fin"] is None


def test_client_gratuit_est_bloque_sur_les_fonctionnalites_payantes(client):
    headers = _register_and_login(client, "plans.gratuit@example.com")

    assert client.get("/api/v1/dettes", headers=headers).status_code == 403
    assert client.get("/api/v1/epargne", headers=headers).status_code == 403
    assert client.get("/api/v1/transactions-recurrentes", headers=headers).status_code == 403
    assert client.get("/api/v1/templates", headers=headers).status_code == 403
    assert client.get("/api/v1/analyse/HABITUDES", headers=headers).status_code == 403
    assert client.get("/api/v1/jarvis/conversations", headers=headers).status_code == 403

    # Les fonctionnalités de base restent accessibles au palier gratuit.
    assert client.get("/api/v1/comptes", headers=headers).status_code == 200
    assert client.get("/api/v1/transactions", headers=headers).status_code == 200
    assert client.get("/api/v1/budgets", headers=headers).status_code == 200
    assert client.get("/api/v1/categories", headers=headers).status_code == 200


def test_changer_plan_vers_essentiel_debloque_dettes_et_epargne(client):
    headers = _register_and_login(client, "plans.essentiel@example.com")

    changement = client.post(
        "/api/v1/abonnement/changer-plan",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL"},
        headers=headers,
    )
    assert changement.status_code == 200
    body = changement.json()
    assert body["plan"]["nom"] == "ESSENTIEL"
    assert body["cycle_facturation"] == "MENSUEL"
    assert body["date_fin"] is not None

    assert client.get("/api/v1/dettes", headers=headers).status_code == 200
    assert client.get("/api/v1/epargne", headers=headers).status_code == 200
    assert client.get("/api/v1/transactions-recurrentes", headers=headers).status_code == 200
    assert client.get("/api/v1/templates", headers=headers).status_code == 200
    # Toujours bloqué : Analyse/JARVIS sont réservés au PREMIUM.
    assert client.get("/api/v1/analyse/HABITUDES", headers=headers).status_code == 403
    assert client.get("/api/v1/jarvis/conversations", headers=headers).status_code == 403


def test_changer_plan_payant_sans_cycle_est_refuse(client):
    headers = _register_and_login(client, "plans.sanscycle@example.com")
    reponse = client.post("/api/v1/abonnement/changer-plan", json={"nom_plan": "PREMIUM"}, headers=headers)
    assert reponse.status_code == 400


def test_changer_plan_inexistant_renvoie_404(client):
    headers = _register_and_login(client, "plans.inexistant@example.com")
    reponse = client.post(
        "/api/v1/abonnement/changer-plan",
        json={"nom_plan": "BUSINESS", "cycle_facturation": "MENSUEL"},
        headers=headers,
    )
    assert reponse.status_code == 404


def test_retour_vers_gratuit_ne_necessite_aucun_cycle(client):
    headers = _register_and_login(client, "plans.retourgratuit@example.com")
    client.post(
        "/api/v1/abonnement/changer-plan",
        json={"nom_plan": "PREMIUM", "cycle_facturation": "ANNUEL"},
        headers=headers,
    )
    retour = client.post("/api/v1/abonnement/changer-plan", json={"nom_plan": "GRATUIT"}, headers=headers)
    assert retour.status_code == 200
    body = retour.json()
    assert body["plan"]["nom"] == "GRATUIT"
    assert body["date_fin"] is None
    assert body["cycle_facturation"] is None

    assert client.get("/api/v1/jarvis/conversations", headers=headers).status_code == 403


def test_abonnement_expire_avec_renouvellement_auto_se_prolonge_tout_seul(client, db_session):
    headers = _register_and_login(client, "plans.renouvellement@example.com")
    client.post(
        "/api/v1/abonnement/changer-plan",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL"},
        headers=headers,
    )

    # Simule une échéance déjà dépassée hier (sans attendre 30 jours réels).
    abonnement = db_session.query(Abonnement).first()
    abonnement.date_fin = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    # Le simple fait de lire l'abonnement déclenche le recalcul (aucune
    # tâche planifiée nécessaire, même principe que Budget/Épargne).
    reponse = client.get("/api/v1/abonnement", headers=headers)
    body = reponse.json()
    assert body["plan"]["nom"] == "ESSENTIEL"  # toujours le même plan
    assert body["date_fin"] > (datetime.utcnow() - timedelta(days=1)).isoformat()  # prolongé
    # L'accès reste donc actif malgré l'échéance dépassée.
    assert client.get("/api/v1/dettes", headers=headers).status_code == 200


def test_annuler_renouvellement_revient_a_gratuit_apres_expiration(client, db_session):
    headers = _register_and_login(client, "plans.annulation@example.com")
    client.post(
        "/api/v1/abonnement/changer-plan",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL"},
        headers=headers,
    )

    annulation = client.post("/api/v1/abonnement/annuler-renouvellement", headers=headers)
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "ANNULE"
    # Toujours accessible jusqu'à la fin de la période déjà "payée".
    assert client.get("/api/v1/dettes", headers=headers).status_code == 200

    # Simule le passage de la date de fin.
    abonnement = db_session.query(Abonnement).first()
    abonnement.date_fin = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    reponse = client.get("/api/v1/abonnement", headers=headers)
    assert reponse.json()["plan"]["nom"] == "GRATUIT"
    assert client.get("/api/v1/dettes", headers=headers).status_code == 403


def test_creer_abonnement_gratuit_est_idempotent_via_get_or_create(client, db_session):
    """
    obtenir_abonnement_actif crée un abonnement GRATUIT de secours si
    aucun n'existe (filet de sécurité) — ne devrait plus arriver en usage
    normal, mais ne doit jamais planter.
    """
    headers = _register_and_login(client, "plans.filet@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]

    db_session.query(Abonnement).filter(Abonnement.id_client == id_client).delete()
    db_session.commit()

    abonnement = plans_service.obtenir_abonnement_actif(db_session, id_client)
    assert abonnement.plan.nom == "GRATUIT"
