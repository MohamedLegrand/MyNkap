from decimal import Decimal

from app.core import hrpay_card
from app.core.hrpay_card import PaiementCarteCree, StatutPaiementCarte
from app.modules.recharges import service as recharges_service
from app.modules.recharges.models import RechargeCompte
from tests.conftest import se_connecter


def _register_and_login(client, email="carte.recharge@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Carte",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _compte_abonnement(client, headers):
    comptes = client.get("/api/v1/comptes", headers=headers).json()
    return next(c for c in comptes if c["type"] == "ABONNEMENT")


def _statut_carte(statut, **kw):
    return StatutPaiementCarte(
        reference=kw.get("reference", "card_ref"),
        statut=statut,
        checkout_url=kw.get("checkout_url"),
        frais=kw.get("frais", Decimal("0")),
        montant_net=kw.get("montant_net", Decimal("0")),
        fraud_review_status=kw.get("fraud_review_status", "NONE"),
    )


def test_initier_recharge_carte_renvoie_checkout_url_et_applique_le_gross_up(client, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.initier@example.com")
    compte = _compte_abonnement(client, headers)

    captures = {}

    def faux_creer(recharge, cpte, cl, ip):
        captures["montant_facture"] = recharge.montant_facture
        captures["devise"] = recharge.devise
        captures["methode"] = recharge.methode
        return PaiementCarteCree(reference="card_abc123", checkout_url="https://pay.enkap.cm/xyz", statut="PENDING")

    monkeypatch.setattr(recharges_service, "_creer_paiement_carte", faux_creer)

    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 10000, "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["methode"] == "CARTE"
    assert body["statut"] == "PENDING"
    assert body["checkout_url"] == "https://pay.enkap.cm/xyz"
    assert body["reference_hrpay"] == "card_abc123"
    # gross-up : ceil(10000 / (1 - 0.035)) = ceil(10362.69...) = 10363
    assert Decimal(body["montant_facture"]) == Decimal("10363")
    assert Decimal(body["montant"]) == Decimal("10000")
    assert captures["devise"] == "XAF"
    assert captures["methode"] == "CARTE"

    # Le compte n'est pas crédité tant que la carte n'est pas capturée.
    solde = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    assert Decimal(solde) == Decimal("0")


def test_initier_recharge_carte_ne_reclame_pas_de_telephone(client, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.sanstel@example.com")
    compte = _compte_abonnement(client, headers)
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_ok", "https://pay/x", "PENDING"),
    )

    # Aucun phone_number / operator dans le corps : accepté pour la carte.
    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 201


def test_recharge_carte_sur_compte_non_abonnement_est_refusee(client, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.nonabo@example.com")
    compte = client.post(
        "/api/v1/comptes",
        json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": 0},
        headers=headers,
    ).json()
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_ok", "https://pay/x", "PENDING"),
    )

    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_recharge_carte_refusee_ne_cree_rien(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.refus@example.com")
    compte = _compte_abonnement(client, headers)

    def refus(*a, **k):
        raise hrpay_card.CartePaiementRefuseError("Paiement refusé par le contrôle anti-fraude.")

    monkeypatch.setattr(recharges_service, "_creer_paiement_carte", refus)

    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 400
    assert db_session.query(RechargeCompte).count() == 0


def test_recharge_carte_service_indisponible_ne_cree_rien(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.panne@example.com")
    compte = _compte_abonnement(client, headers)

    def panne(*a, **k):
        raise hrpay_card.ServiceCarteIndisponibleError("HR-Skills Pay a répondu 503.")

    monkeypatch.setattr(recharges_service, "_creer_paiement_carte", panne)

    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 503
    assert db_session.query(RechargeCompte).count() == 0


def test_recharge_carte_gelee_en_revue_antifraude_sans_checkout_url(client, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.fraude@example.com")
    compte = _compte_abonnement(client, headers)
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_gelee", checkout_url=None, statut="PENDING"),
    )

    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "PENDING"
    assert body["checkout_url"] is None
    assert body["reference_hrpay"] == "card_gelee"


def test_verifier_recharges_carte_capturee_credite_le_montant_demande(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.capture@example.com")
    compte = _compte_abonnement(client, headers)
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_capture", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 10000, "methode": "CARTE"},
        headers=headers,
    )

    monkeypatch.setattr(recharges_service, "_lire_paiement_carte", lambda ref: _statut_carte("CAPTURED"))
    nb_traites = recharges_service.verifier_recharges_en_attente(db_session)
    assert nb_traites == 1

    recharge = db_session.query(RechargeCompte).first()
    assert recharge.statut == "SUCCESS"
    assert recharge.date_confirmation is not None
    assert recharge.id_transaction is not None

    # Crédité du montant demandé (10000), pas du montant facturé carte (gross-up).
    solde = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    assert Decimal(solde) == Decimal("10000")

    transactions = client.get("/api/v1/transactions", headers=headers).json()
    depot = next(t for t in transactions if t["id_transaction"] == recharge.id_transaction)
    assert depot["type"] == "DEPOT_INITIAL"
    assert "carte" in depot["description"].lower()


def test_verifier_recharges_carte_echouee_ne_credite_pas(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.echec@example.com")
    compte = _compte_abonnement(client, headers)
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_echec", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 10000, "methode": "CARTE"},
        headers=headers,
    )

    monkeypatch.setattr(recharges_service, "_lire_paiement_carte", lambda ref: _statut_carte("CANCELED"))
    recharges_service.verifier_recharges_en_attente(db_session)

    recharge = db_session.query(RechargeCompte).first()
    assert recharge.statut == "FAILED"
    solde = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    assert Decimal(solde) == Decimal("0")


def test_verifier_recharges_carte_toujours_pending_est_ignoree(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.pending@example.com")
    compte = _compte_abonnement(client, headers)
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_pending", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )

    # AUTHORIZED est transitoire côté E-NKAP -> reste PENDING chez nous.
    monkeypatch.setattr(recharges_service, "_lire_paiement_carte", lambda ref: _statut_carte("AUTHORIZED"))
    nb_traites = recharges_service.verifier_recharges_en_attente(db_session)
    assert nb_traites == 0
    assert db_session.query(RechargeCompte).first().statut == "PENDING"


def test_verifier_recharges_carte_erreur_reseau_reste_pending(client, db_session, monkeypatch):
    headers = _register_and_login(client, "carte.recharge.reseau@example.com")
    compte = _compte_abonnement(client, headers)
    monkeypatch.setattr(
        recharges_service, "_creer_paiement_carte",
        lambda *a, **k: PaiementCarteCree("card_reseau", "https://pay/x", "PENDING"),
    )
    client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "methode": "CARTE"},
        headers=headers,
    )

    def indispo(ref):
        raise hrpay_card.ServiceCarteIndisponibleError("timeout")

    monkeypatch.setattr(recharges_service, "_lire_paiement_carte", indispo)
    nb_traites = recharges_service.verifier_recharges_en_attente(db_session)
    assert nb_traites == 0
    assert db_session.query(RechargeCompte).first().statut == "PENDING"
