import pytest
from decimal import Decimal
from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur, Client
from app.modules.plans.models import Abonnement, PaiementAbonnement, Plan

def _create_admin(db_session, username="planadmin", email="planadmin@mynkap.cm", password="adminpassword123", niveau_acces=3):
    admin = Administrateur(
        username=username,
        email=email,
        mot_de_passe=get_password_hash(password),
        niveau_acces=niveau_acces,
        est_actif=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    token = create_access_token(subject=admin.id_administrateur)
    return admin, {"Authorization": f"Bearer {token}"}

def _create_client(db_session, email="clientplan@mynkap.cm", password="clientpassword123"):
    c = Client(
        email=email,
        first_name="Samuel",
        last_name="Etoo",
        phone="+237699999999",
        mot_de_passe=get_password_hash(password),
        est_actif=True,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    
    token = create_access_token(subject=c.id_client)
    return c, {"Authorization": f"Bearer {token}"}

def test_admin_overview_et_lister_abonnements_et_paiements(client, db_session):
    admin, admin_headers = _create_admin(db_session)

    # 1. Overview
    res_ov = client.get("/api/v1/admin/abonnements/overview", headers=admin_headers)
    assert res_ov.status_code == 200
    data_ov = res_ov.json()
    assert "total_abonnes" in data_ov
    assert "repartition_plans" in data_ov
    assert "repartition_statuts" in data_ov

    # 2. Lister les abonnements
    res_ab = client.get("/api/v1/admin/abonnements", headers=admin_headers)
    assert res_ab.status_code == 200
    assert "items" in res_ab.json()

    # 3. Lister les paiements
    res_pay = client.get("/api/v1/admin/paiements", headers=admin_headers)
    assert res_pay.status_code == 200
    assert "items" in res_pay.json()

def test_admin_forcer_abonnement_client(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="forceradmin", email="forceradmin@mynkap.cm", niveau_acces=2)
    user_c, _ = _create_client(db_session, email="forcee@mynkap.cm")

    premium_plan = db_session.query(Plan).filter(Plan.nom == "PREMIUM").first()
    assert premium_plan is not None

    res_force = client.post(
        f"/api/v1/admin/clients/{user_c.id_client}/abonnement/forcer",
        json={
            "id_plan": premium_plan.id_plan,
            "cycle_facturation": "ANNUEL",
            "statut": "ACTIF",
            "duree_jours": 365,
            "raison": "Geste commercial support VIP",
        },
        headers=admin_headers,
    )
    assert res_force.status_code == 200
    data = res_force.json()
    assert data["nom_plan"] == "PREMIUM"
    assert data["statut"] == "ACTIF"
    assert data["cycle_facturation"] == "ANNUEL"

    # Vérification AuditLog
    log = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_FORCER_ABONNEMENT",
        AuditLog.id_ressource == data["id_abonnement"]
    ).first()
    assert log is not None

def test_admin_valider_paiement_manuel(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="valadmin", email="valadmin@mynkap.cm", niveau_acces=2)
    user_c, _ = _create_client(db_session, email="payee@mynkap.cm")

    essentiel_plan = db_session.query(Plan).filter(Plan.nom == "ESSENTIEL").first()
    assert essentiel_plan is not None

    # Création d'un paiement PENDING
    paiement = PaiementAbonnement(
        id_client=user_c.id_client,
        id_plan_demande=essentiel_plan.id_plan,
        cycle_facturation="MENSUEL",
        montant=Decimal("2000.00"),
        devise="XAF",
        reference_hrpay="HRPAY_TEST_LITIGE_123",
        statut="PENDING",
    )
    db_session.add(paiement)
    db_session.commit()
    db_session.refresh(paiement)

    # Validation manuelle par l'admin -> 200 OK
    res_val = client.post(
        f"/api/v1/admin/paiements/{paiement.id_paiement}/valider-manuel",
        json={"raison": "Preuve de virement reçue par mail"},
        headers=admin_headers,
    )
    assert res_val.status_code == 200
    data_val = res_val.json()
    assert data_val["statut"] == "SUCCESS"

    # Vérification que le plan du client est passé à ESSENTIEL
    ab = db_session.query(Abonnement).filter(Abonnement.id_client == user_c.id_client).first()
    assert ab is not None
    assert ab.id_plan == essentiel_plan.id_plan
    assert ab.statut == "ACTIF"

    # AuditLog généré
    log = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_VALIDER_PAIEMENT_MANUEL",
        AuditLog.id_ressource == paiement.id_paiement
    ).first()
    assert log is not None

def test_admin_plans_restrictions_droits(client, db_session):
    # Admin niveau 1 (Support)
    _, l1_headers = _create_admin(db_session, username="planl1", email="planl1@mynkap.cm", niveau_acces=1)
    
    # Client normal
    user_c, c_headers = _create_client(db_session, email="normalplan@mynkap.cm")

    premium_plan = db_session.query(Plan).filter(Plan.nom == "PREMIUM").first()

    # 1. Admin Niveau 1 peut consulter l'overview -> 200 OK
    res_l1_ov = client.get("/api/v1/admin/abonnements/overview", headers=l1_headers)
    assert res_l1_ov.status_code == 200

    # 2. Admin Niveau 1 NE PEUT PAS forcer un abonnement -> 403 Forbidden
    res_l1_force = client.post(
        f"/api/v1/admin/clients/{user_c.id_client}/abonnement/forcer",
        json={"id_plan": premium_plan.id_plan, "statut": "ACTIF"},
        headers=l1_headers,
    )
    assert res_l1_force.status_code == 403

    # 3. Client normal NE PEUT PAS consulter -> 403 Forbidden
    res_c_ov = client.get("/api/v1/admin/abonnements/overview", headers=c_headers)
    assert res_c_ov.status_code == 403
