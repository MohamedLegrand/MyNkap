import hrpay
import pytest
from decimal import Decimal

from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur
from app.modules.plans import service as plans_service
from app.modules.plans.models import Retrait


def _create_admin(db_session, username="retraitadmin", email="retraitadmin@mynkap.cm", niveau_acces=3):
    admin = Administrateur(
        username=username,
        email=email,
        mot_de_passe=get_password_hash("adminpassword123"),
        niveau_acces=niveau_acces,
        est_actif=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    token = create_access_token(subject=admin.id_administrateur)
    return admin, {"Authorization": f"Bearer {token}"}


RETRAIT_PAYLOAD = {
    "montant": "50000",
    "devise": "XAF",
    "phone_number": "237690000000",
    "operator": "ORANGE",
    "pays": "CM",
    "raison": "Retrait mensuel du chiffre d'affaires",
}


def test_solde_wallet_niveau1_est_refuse(client, db_session):
    _, headers = _create_admin(db_session, niveau_acces=1)
    reponse = client.get("/api/v1/admin/wallet/solde", headers=headers)
    assert reponse.status_code == 403


def test_solde_wallet_niveau2_ok(client, db_session, monkeypatch):
    _, headers = _create_admin(db_session, niveau_acces=2)
    monkeypatch.setattr(
        plans_service, "obtenir_solde_wallet",
        lambda: {"devise": "XAF", "disponible": 150000, "en_attente": 20000, "gele": False},
    )
    reponse = client.get("/api/v1/admin/wallet/solde", headers=headers)
    assert reponse.status_code == 200
    body = reponse.json()
    assert Decimal(body["disponible"]) == Decimal("150000")
    assert body["gele"] is False


def test_initier_retrait_niveau2_est_refuse(client, db_session, monkeypatch):
    """Voir le solde (niveau 2+) et déclencher un retrait (niveau 3) sont
    deux garde-fous distincts — un Modérateur peut consulter mais pas agir."""
    _, headers = _create_admin(db_session, niveau_acces=2)
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", lambda *a, **k: "ref_ne_devrait_jamais_etre_appele")

    reponse = client.post("/api/v1/admin/retraits", json=RETRAIT_PAYLOAD, headers=headers)
    assert reponse.status_code == 403
    assert db_session.query(Retrait).count() == 0


def test_initier_retrait_superadmin_cree_un_retrait_pending(client, db_session, monkeypatch):
    admin, headers = _create_admin(db_session, niveau_acces=3)

    appels = {}

    def fausse_reference(phone_number, operator, montant, devise, country, id_retrait):
        appels["phone_number"] = phone_number
        appels["operator"] = operator
        appels["country"] = country
        return "ref_retrait_123"

    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", fausse_reference)

    reponse = client.post("/api/v1/admin/retraits", json=RETRAIT_PAYLOAD, headers=headers)
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "PENDING"
    assert body["reference_hrpay"] == "ref_retrait_123"
    assert body["username_administrateur"] == admin.username
    assert Decimal(body["montant"]) == Decimal("50000")
    assert appels["phone_number"] == "237690000000"
    assert appels["operator"] == "ORANGE"
    assert appels["country"] == "CM"

    log = db_session.query(AuditLog).filter(AuditLog.action == "ADMIN_INITIER_RETRAIT").first()
    assert log is not None
    assert log.id_ressource == body["id_retrait"]


def test_verifier_retraits_en_attente_confirme_le_statut(client, db_session, monkeypatch):
    _, headers = _create_admin(db_session, niveau_acces=3)
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", lambda *a, **k: "ref_retrait_success")

    client.post("/api/v1/admin/retraits", json=RETRAIT_PAYLOAD, headers=headers)

    monkeypatch.setattr(plans_service, "_verifier_statut_hrpay", lambda reference: "SUCCESS")
    nb_traites = plans_service.verifier_retraits_en_attente(db_session)
    assert nb_traites == 1

    retrait = db_session.query(Retrait).first()
    assert retrait.statut == "SUCCESS"
    assert retrait.date_confirmation is not None


def test_initier_retrait_solde_insuffisant_renvoie_402(client, db_session, monkeypatch):
    _, headers = _create_admin(db_session, niveau_acces=3)

    def solde_insuffisant(*a, **k):
        raise hrpay.WalletError("solde disponible insuffisant", status_code=402, code="INSUFFICIENT_BALANCE")

    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", solde_insuffisant)

    reponse = client.post("/api/v1/admin/retraits", json=RETRAIT_PAYLOAD, headers=headers)
    assert reponse.status_code == 402
    assert db_session.query(Retrait).count() == 0


def test_initier_retrait_pays_invalide_renvoie_400(client, db_session, monkeypatch):
    _, headers = _create_admin(db_session, niveau_acces=3)
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", lambda *a, **k: "ne_devrait_jamais_etre_appele")

    payload = {**RETRAIT_PAYLOAD, "pays": "US"}
    reponse = client.post("/api/v1/admin/retraits", json=payload, headers=headers)
    assert reponse.status_code == 400
    assert db_session.query(Retrait).count() == 0


def test_initier_retrait_operateur_indisponible_pour_le_pays_renvoie_400(client, db_session, monkeypatch):
    _, headers = _create_admin(db_session, niveau_acces=3)
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", lambda *a, **k: "ne_devrait_jamais_etre_appele")

    # WAVE n'existe pas au Cameroun (voir hrpay.operators_for_country("CM")).
    payload = {**RETRAIT_PAYLOAD, "operator": "WAVE"}
    reponse = client.post("/api/v1/admin/retraits", json=payload, headers=headers)
    assert reponse.status_code == 400
    assert db_session.query(Retrait).count() == 0


def test_lister_retraits_admin(client, db_session, monkeypatch):
    _, headers = _create_admin(db_session, niveau_acces=3)
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_out", lambda *a, **k: "ref_liste")

    client.post("/api/v1/admin/retraits", json=RETRAIT_PAYLOAD, headers=headers)

    reponse = client.get("/api/v1/admin/retraits", headers=headers)
    assert reponse.status_code == 200
    body = reponse.json()
    assert body["total"] == 1
    assert body["items"][0]["reference_hrpay"] == "ref_liste"
