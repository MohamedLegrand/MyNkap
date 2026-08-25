from decimal import Decimal

import hrpay

from app.modules.recharges import service as recharges_service
from app.modules.recharges.models import RechargeCompte
from tests.conftest import se_connecter


def _register_and_login(client, email="recharge.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Recharge",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _creer_compte(client, headers, solde_initial=0):
    return client.post(
        "/api/v1/comptes",
        json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def test_initier_recharge_cree_une_recharge_pending(client, monkeypatch):
    headers = _register_and_login(client, "recharge.initier@example.com")
    compte = _creer_compte(client, headers)

    appels = {}

    def fausse_reference(phone_number, operator, montant, devise, country, id_recharge):
        appels["phone_number"] = phone_number
        appels["montant"] = montant
        appels["country"] = country
        return "ref_test_123"

    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", fausse_reference)

    reponse = client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte["id_compte"], "montant": 10000,
            "phone_number": "237655500393", "operator": "orange", "pays": "CM",
        },
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "PENDING"
    assert body["reference_hrpay"] == "ref_test_123"
    assert Decimal(body["montant"]) == Decimal("10000")
    assert appels["phone_number"] == "237655500393"
    assert appels["country"] == "CM"

    # Le compte n'est pas encore crédité : la recharge n'est pas confirmée.
    solde = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    assert Decimal(solde) == Decimal("0")


def test_initier_recharge_sur_compte_dun_autre_client_est_refuse(client, monkeypatch):
    headers_a = _register_and_login(client, "recharge.a@example.com")
    headers_b = _register_and_login(client, "recharge.b@example.com")
    compte_a = _creer_compte(client, headers_a)
    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_test")

    reponse = client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte_a["id_compte"], "montant": 5000,
            "phone_number": "237655500393", "operator": "orange", "pays": "CM",
        },
        headers=headers_b,
    )
    assert reponse.status_code == 404


def test_initier_recharge_sans_telephone_est_refuse(client, monkeypatch):
    headers = _register_and_login(client, "recharge.sanstelephone@example.com")
    compte = _creer_compte(client, headers)
    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_test")

    reponse = client.post(
        "/api/v1/recharges",
        json={"id_compte": compte["id_compte"], "montant": 5000, "phone_number": "", "operator": "mtn", "pays": "CM"},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_initier_recharge_echec_hrpay_ne_cree_rien(client, db_session, monkeypatch):
    headers = _register_and_login(client, "recharge.echechrpay@example.com")
    compte = _creer_compte(client, headers)

    def echec(*a, **k):
        raise hrpay.HRPayError("panne réseau")

    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", echec)

    reponse = client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte["id_compte"], "montant": 5000,
            "phone_number": "237655500393", "operator": "mtn", "pays": "CM",
        },
        headers=headers,
    )
    assert reponse.status_code == 503
    assert db_session.query(RechargeCompte).count() == 0


def test_verifier_recharges_en_attente_confirme_et_credite_le_compte(client, db_session, monkeypatch):
    headers = _register_and_login(client, "recharge.confirmation@example.com")
    compte = _creer_compte(client, headers, solde_initial=2000)
    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_success")

    client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte["id_compte"], "montant": 10000,
            "phone_number": "237655500393", "operator": "orange", "pays": "CM",
        },
        headers=headers,
    )

    monkeypatch.setattr(recharges_service, "_verifier_statut_hrpay", lambda reference: "SUCCESS")
    nb_traites = recharges_service.verifier_recharges_en_attente(db_session)
    assert nb_traites == 1

    recharge = db_session.query(RechargeCompte).first()
    assert recharge.statut == "SUCCESS"
    assert recharge.date_confirmation is not None
    assert recharge.id_transaction is not None

    # Le compte est réellement crédité (2000 initial + 10000 rechargés).
    solde = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    assert Decimal(solde) == Decimal("12000")

    # Traçable comme un DEPOT_INITIAL, sans catégorie forcée.
    transactions = client.get("/api/v1/transactions", headers=headers).json()
    depot_recharge = next(t for t in transactions if t["id_transaction"] == recharge.id_transaction)
    assert depot_recharge["type"] == "DEPOT_INITIAL"
    assert depot_recharge["id_categorie"] is None
    assert Decimal(depot_recharge["montant"]) == Decimal("10000")


def test_verifier_recharges_en_attente_marque_failed_sans_crediter(client, db_session, monkeypatch):
    headers = _register_and_login(client, "recharge.echecconfirmation@example.com")
    compte = _creer_compte(client, headers, solde_initial=2000)
    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_failed")

    client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte["id_compte"], "montant": 10000,
            "phone_number": "237655500393", "operator": "orange", "pays": "CM",
        },
        headers=headers,
    )

    monkeypatch.setattr(recharges_service, "_verifier_statut_hrpay", lambda reference: "FAILED")
    recharges_service.verifier_recharges_en_attente(db_session)

    recharge = db_session.query(RechargeCompte).first()
    assert recharge.statut == "FAILED"

    solde = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    assert Decimal(solde) == Decimal("2000")


def test_verifier_recharges_en_attente_ignore_ceux_toujours_pending(client, db_session, monkeypatch):
    headers = _register_and_login(client, "recharge.toujourspending@example.com")
    compte = _creer_compte(client, headers)
    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_pending")

    client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte["id_compte"], "montant": 5000,
            "phone_number": "237655500393", "operator": "orange", "pays": "CM",
        },
        headers=headers,
    )

    monkeypatch.setattr(recharges_service, "_verifier_statut_hrpay", lambda reference: "PENDING")
    nb_traites = recharges_service.verifier_recharges_en_attente(db_session)
    assert nb_traites == 0

    recharge = db_session.query(RechargeCompte).first()
    assert recharge.statut == "PENDING"


def test_obtenir_recharge_dun_autre_client_renvoie_404(client, monkeypatch):
    headers_a = _register_and_login(client, "recharge.priv.a@example.com")
    headers_b = _register_and_login(client, "recharge.priv.b@example.com")
    compte_a = _creer_compte(client, headers_a)
    monkeypatch.setattr(recharges_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_prive")

    recharge = client.post(
        "/api/v1/recharges",
        json={
            "id_compte": compte_a["id_compte"], "montant": 5000,
            "phone_number": "237655500393", "operator": "orange", "pays": "CM",
        },
        headers=headers_a,
    ).json()

    reponse = client.get(f"/api/v1/recharges/{recharge['id_recharge']}", headers=headers_b)
    assert reponse.status_code == 404
