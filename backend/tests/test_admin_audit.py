import pytest
from datetime import datetime, timedelta
from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.audit.service import enregistrer_action
from app.modules.auth.models import Administrateur, Client

def _create_admin(db_session, username="auditadmin", email="auditadmin@mynkap.cm", password="adminpassword123"):
    admin = Administrateur(
        username=username,
        email=email,
        mot_de_passe=get_password_hash(password),
        niveau_acces=3,
        est_actif=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    token = create_access_token(subject=admin.id_administrateur)
    return admin, {"Authorization": f"Bearer {token}"}

def _create_client(db_session, email="clientaudit@mynkap.cm", password="clientpassword123"):
    c = Client(
        email=email,
        first_name="Jean",
        last_name="Dupont",
        phone="+237600000099",
        mot_de_passe=get_password_hash(password),
        est_actif=True,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    
    token = create_access_token(subject=c.id_client)
    return c, {"Authorization": f"Bearer {token}"}

def test_admin_lister_et_filtrer_audit_logs(client, db_session):
    admin, admin_headers = _create_admin(db_session)
    user_c, _ = _create_client(db_session)

    # Création d'entrées d'audit de test
    log1 = enregistrer_action(
        db_session,
        id_utilisateur=user_c.id_client,
        action="TEST_ACTION_A",
        ressource="TRANSACTION",
        id_ressource=101,
        donnees_avant={"montant": 100},
        donnees_apres={"montant": 150},
    )
    log2 = enregistrer_action(
        db_session,
        id_utilisateur=admin.id_administrateur,
        action="TEST_ACTION_B",
        ressource="ADMINISTRATEUR",
        id_ressource=admin.id_administrateur,
    )

    # 1. Liste sans filtre -> Retourne au moins log1 et log2
    res_all = client.get("/api/v1/admin/audit", headers=admin_headers)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] >= 2
    assert any(item["id_audit"] == log1.id_audit for item in data_all["items"])
    assert any(item["id_audit"] == log2.id_audit for item in data_all["items"])

    # 2. Filtre par action
    res_action = client.get("/api/v1/admin/audit?action=TEST_ACTION_A", headers=admin_headers)
    assert res_action.status_code == 200
    data_action = res_action.json()
    assert all(item["action"] == "TEST_ACTION_A" for item in data_action["items"])

    # 3. Filtre par ressource
    res_ressource = client.get("/api/v1/admin/audit?ressource=TRANSACTION", headers=admin_headers)
    assert res_ressource.status_code == 200
    data_ressource = res_ressource.json()
    assert all(item["ressource"] == "TRANSACTION" for item in data_ressource["items"])

    # 4. Filtre par id_utilisateur
    res_user = client.get(f"/api/v1/admin/audit?id_utilisateur={user_c.id_client}", headers=admin_headers)
    assert res_user.status_code == 200
    data_user = res_user.json()
    assert all(item["id_utilisateur"] == user_c.id_client for item in data_user["items"])

def test_admin_obtenir_detail_audit_log(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="detailadmin", email="detailadmin@mynkap.cm")

    log_entry = enregistrer_action(
        db_session,
        id_utilisateur=admin.id_administrateur,
        action="MODIFIER_CONFIG",
        ressource="CONFIG",
        id_ressource=5,
        donnees_avant={"seuil": 80},
        donnees_apres={"seuil": 90},
    )

    # 1. Consultation d'une entrée existante -> 200 OK
    res_detail = client.get(f"/api/v1/admin/audit/{log_entry.id_audit}", headers=admin_headers)
    assert res_detail.status_code == 200
    data = res_detail.json()
    assert data["id_audit"] == log_entry.id_audit
    assert data["email_utilisateur"] == admin.email
    assert data["action"] == "MODIFIER_CONFIG"
    assert data["donnees_avant"] == {"seuil": 80}
    assert data["donnees_apres"] == {"seuil": 90}

    # 2. ID inexistant -> 404 Not Found
    res_404 = client.get("/api/v1/admin/audit/999999", headers=admin_headers)
    assert res_404.status_code == 404

def test_admin_statistiques_audit(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="statsadmin", email="statsadmin@mynkap.cm")

    enregistrer_action(db_session, id_utilisateur=admin.id_administrateur, action="STAT_ACTION_1", ressource="TEST")
    enregistrer_action(db_session, id_utilisateur=admin.id_administrateur, action="STAT_ACTION_1", ressource="TEST")

    res_stats = client.get("/api/v1/admin/audit/stats", headers=admin_headers)
    assert res_stats.status_code == 200
    data = res_stats.json()
    assert data["total_logs"] >= 2
    assert isinstance(data["repartition_actions"], list)

def test_audit_admin_rejet_non_admin(client, db_session):
    client_user, client_headers = _create_client(db_session, email="normaluser@mynkap.cm")

    res_forbidden = client.get("/api/v1/admin/audit", headers=client_headers)
    assert res_forbidden.status_code == 403
