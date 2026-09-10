from decimal import Decimal

from app.core import hrpay_card
from app.core.hrpay_card import PaiementCarteCree, StatutPaiementCarte
from app.modules.plans import service as plans_service
from app.modules.plans.models import PaiementAbonnement
from tests.conftest import se_connecter


def _register_and_login(client, email="carte.plan@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Carte",
            "last_name": "Plan",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _statut_carte(statut, **kw):
    return StatutPaiementCarte(
        reference=kw.get("reference", "card_ref"),
        statut=statut,
        checkout_url=kw.get("checkout_url"),
        frais=kw.get("frais", Decimal("0")),
        montant_net=kw.get("montant_net", Decimal("0")),
        fraud_review_status=kw.get("fraud_review_status", "NONE"),
    )


def test_initier_paiement_carte_renvoie_checkout_url_et_gross_up(client, monkeypatch):
    headers = _register_and_login(client, "carte.plan.initier@example.com")

    captures = {}

    def faux_creer(paiement, plan, cl, ip):
        captures["montant_facture"] = paiement.montant_facture
        captures["devise"] = paiement.devise
        captures["methode"] = paiement.methode
        return PaiementCarteCree(reference="card_p1", checkout_url="https://pay.enkap.cm/p1", statut="PENDING")

    monkeypatch.setattr(plans_service, "_creer_paiement_carte", faux_creer)

    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL", "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["methode"] == "CARTE"
    assert body["statut"] == "PENDING"
    assert body["checkout_url"] == "https://pay.enkap.cm/p1"
    assert body["reference_hrpay"] == "card_p1"
    assert Decimal(body["montant"]) == Decimal("2500")  # prix de référence XAF
    # gross-up : ceil(2500 / (1 - 0.035)) = ceil(2590.67...) = 2591
    assert Decimal(body["montant_facture"]) == Decimal("2591")
    assert captures["devise"] == "XAF"
    assert captures["methode"] == "CARTE"

    # Le plan n'a pas encore changé (paiement pas confirmé).
    assert client.get("/api/v1/abonnement", headers=headers).json()["plan"]["nom"] != "ESSENTIEL"


def test_initier_paiement_carte_ne_reclame_pas_de_telephone(client, monkeypatch):
    headers = _register_and_login(client, "carte.plan.sanstel@example.com")
    monkeypatch.setattr(
        plans_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_ok", "https://pay/x", "PENDING"),
    )
    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "PREMIUM", "cycle_facturation": "ANNUEL", "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 201


def test_paiement_carte_refuse_ne_cree_rien(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.plan.refus@example.com")

    def refus(*a, **k):
        raise hrpay_card.CartePaiementRefuseError("Le montant dépasse le plafond autorisé par opération.")

    monkeypatch.setattr(plans_service, "_creer_paiement_carte", refus)

    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "PREMIUM", "cycle_facturation": "MENSUEL", "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 400
    assert db_session.query(PaiementAbonnement).count() == 0


def test_paiement_carte_service_indisponible_ne_cree_rien(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.plan.panne@example.com")

    def panne(*a, **k):
        raise hrpay_card.ServiceCarteIndisponibleError("HR-Skills Pay a répondu 502.")

    monkeypatch.setattr(plans_service, "_creer_paiement_carte", panne)

    reponse = client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL", "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 503
    assert db_session.query(PaiementAbonnement).count() == 0


def test_verifier_paiements_carte_capture_applique_le_plan(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.plan.capture@example.com")
    monkeypatch.setattr(
        plans_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_cap", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL", "methode": "CARTE"},
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_lire_paiement_carte", lambda ref: _statut_carte("CAPTURED"))
    nb_traites = plans_service.verifier_paiements_en_attente(db_session)
    assert nb_traites == 1

    paiement = db_session.query(PaiementAbonnement).first()
    assert paiement.statut == "SUCCESS"
    assert paiement.date_confirmation is not None

    abonnement = client.get("/api/v1/abonnement", headers=headers).json()
    assert abonnement["plan"]["nom"] == "ESSENTIEL"


def test_verifier_paiements_carte_echec_ne_change_pas_le_plan(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.plan.echec@example.com")
    monkeypatch.setattr(
        plans_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_ko", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "PREMIUM", "cycle_facturation": "MENSUEL", "methode": "CARTE"},
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_lire_paiement_carte", lambda ref: _statut_carte("FAILED"))
    plans_service.verifier_paiements_en_attente(db_session)

    paiement = db_session.query(PaiementAbonnement).first()
    assert paiement.statut == "FAILED"
    assert client.get("/api/v1/abonnement", headers=headers).json()["plan"]["nom"] != "PREMIUM" or \
        client.get("/api/v1/abonnement", headers=headers).json()["statut"] == "ESSAI"


def test_verifier_paiements_carte_pending_est_ignore(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.plan.pending@example.com")
    monkeypatch.setattr(
        plans_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_pend", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/abonnement/paiements",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL", "methode": "CARTE"},
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_lire_paiement_carte", lambda ref: _statut_carte("PENDING"))
    nb_traites = plans_service.verifier_paiements_en_attente(db_session)
    assert nb_traites == 0
    assert db_session.query(PaiementAbonnement).first().statut == "PENDING"
