from datetime import datetime, timedelta
from decimal import Decimal

import hrpay

from app.modules.plans import service as plans_service
from app.modules.plans.models import Abonnement, PaiementAbonnement
from tests.conftest import se_connecter_avec_otp


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
    access_token = se_connecter_avec_otp(client, email, mot_de_passe).json()["access_token"]
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


def test_changer_plan_naccepte_que_gratuit(client):
    headers = _register_and_login(client, "plans.changerplan@example.com")

    retour = client.post("/api/v1/abonnement/changer-plan", json={"nom_plan": "GRATUIT"}, headers=headers)
    assert retour.status_code == 200
    assert retour.json()["plan"]["nom"] == "GRATUIT"

    # Un plan payant n'est plus acceptable via cet endpoint (voir
    # /abonnement/paiements) — rejeté dès la validation Pydantic.
    refuse = client.post("/api/v1/abonnement/changer-plan", json={"nom_plan": "PREMIUM"}, headers=headers)
    assert refuse.status_code == 422


# --- Paiement Mobile Money (HR-Skills Pay), toujours mocké dans les tests ---

def test_initier_paiement_cree_un_paiement_pending(client, monkeypatch):
    headers = _register_and_login(client, "plans.paiement@example.com")

    appels = {}

    def fausse_reference(phone_number, operator, montant, devise, id_paiement):
        appels["phone_number"] = phone_number
        appels["operator"] = operator
        appels["montant"] = montant
        return "ref_test_123"

    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", fausse_reference)

    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "PENDING"
    assert body["reference_hrpay"] == "ref_test_123"
    assert body["plan_demande"]["nom"] == "ESSENTIEL"
    assert Decimal(body["montant"]) == Decimal("1000")
    assert appels["phone_number"] == "237655500393"
    assert appels["operator"] == "orange"

    # Le plan n'a pas encore changé : le paiement n'est pas confirmé.
    assert client.get("/api/v1/dettes", headers=headers).status_code == 403


def test_initier_paiement_sans_telephone_est_refuse(client, monkeypatch):
    headers = _register_and_login(client, "plans.sanstelephone@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_test")

    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL", "phone_number": "", "operator": "mtn"},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_initier_paiement_echec_hrpay_ne_cree_rien(client, db_session, monkeypatch):
    headers = _register_and_login(client, "plans.echechrpay@example.com")

    def echec(*a, **k):
        raise hrpay.HRPayError("panne réseau")

    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", echec)

    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "PREMIUM",
            "cycle_facturation": "ANNUEL",
            "phone_number": "237655500393",
            "operator": "mtn",
        },
        headers=headers,
    )
    assert reponse.status_code == 503
    assert db_session.query(PaiementAbonnement).count() == 0


def test_verifier_paiements_en_attente_confirme_et_applique_le_plan(client, db_session, monkeypatch):
    headers = _register_and_login(client, "plans.confirmation@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_success")

    client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_verifier_statut_hrpay", lambda reference: "SUCCESS")
    nb_traites = plans_service.verifier_paiements_en_attente(db_session)
    assert nb_traites == 1

    paiement = db_session.query(PaiementAbonnement).first()
    assert paiement.statut == "SUCCESS"
    assert paiement.date_confirmation is not None

    # Le plan est maintenant réellement changé.
    abonnement = client.get("/api/v1/abonnement", headers=headers).json()
    assert abonnement["plan"]["nom"] == "ESSENTIEL"
    assert client.get("/api/v1/dettes", headers=headers).status_code == 200


def test_verifier_paiements_en_attente_marque_failed_sans_changer_le_plan(client, db_session, monkeypatch):
    headers = _register_and_login(client, "plans.echecconfirmation@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_failed")

    client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_verifier_statut_hrpay", lambda reference: "FAILED")
    plans_service.verifier_paiements_en_attente(db_session)

    paiement = db_session.query(PaiementAbonnement).first()
    assert paiement.statut == "FAILED"

    abonnement = client.get("/api/v1/abonnement", headers=headers).json()
    assert abonnement["plan"]["nom"] == "GRATUIT"
    assert client.get("/api/v1/dettes", headers=headers).status_code == 403


def test_verifier_paiements_en_attente_ignore_ceux_toujours_pending(client, db_session, monkeypatch):
    headers = _register_and_login(client, "plans.toujourspending@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_pending")

    client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_verifier_statut_hrpay", lambda reference: "PENDING")
    nb_traites = plans_service.verifier_paiements_en_attente(db_session)
    assert nb_traites == 0

    paiement = db_session.query(PaiementAbonnement).first()
    assert paiement.statut == "PENDING"


def test_obtenir_paiement_dun_autre_client_renvoie_404(client, monkeypatch):
    headers_a = _register_and_login(client, "plans.paiement.a@example.com")
    headers_b = _register_and_login(client, "plans.paiement.b@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_prive")

    paiement = client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers_a,
    ).json()

    reponse = client.get(f"/api/v1/abonnement/paiements/{paiement['id_paiement']}", headers=headers_b)
    assert reponse.status_code == 404


def test_abonnement_expire_revient_a_gratuit_meme_avec_renouvellement_auto(client, db_session):
    """
    Depuis l'intégration HR-Skills Pay, aucun renouvellement n'est simulé
    — même avec renouvellement_auto=True, l'échéance dépassée fait
    toujours revenir à GRATUIT (voir plans.service.obtenir_abonnement_actif).
    """
    headers = _register_and_login(client, "plans.expiration@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    plans_service.changer_plan(db_session, id_client, "ESSENTIEL", "MENSUEL")

    abonnement = db_session.query(Abonnement).first()
    assert abonnement.renouvellement_auto is True
    abonnement.date_fin = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    reponse = client.get("/api/v1/abonnement", headers=headers)
    assert reponse.json()["plan"]["nom"] == "GRATUIT"
    assert client.get("/api/v1/dettes", headers=headers).status_code == 403


def test_annuler_renouvellement_garde_lacces_jusqua_la_date_fin(client, db_session):
    headers = _register_and_login(client, "plans.annulation@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    plans_service.changer_plan(db_session, id_client, "ESSENTIEL", "MENSUEL")

    annulation = client.post("/api/v1/abonnement/annuler-renouvellement", headers=headers)
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "ANNULE"
    # Toujours accessible jusqu'à la fin de la période déjà payée.
    assert client.get("/api/v1/dettes", headers=headers).status_code == 200


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
