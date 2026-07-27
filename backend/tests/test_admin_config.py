import pytest
from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur, Client

def _create_admin(db_session, username="cfgadmin", email="cfgadmin@mynkap.cm", password="adminpassword123", niveau_acces=3):
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

def _create_client(db_session, email="clientcfg@mynkap.cm", password="clientpassword123"):
    c = Client(
        email=email,
        first_name="Paul",
        last_name="Biya",
        phone="+237600000088",
        mot_de_passe=get_password_hash(password),
        est_actif=True,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    
    token = create_access_token(subject=c.id_client)
    return c, {"Authorization": f"Bearer {token}"}

def test_admin_creer_et_modifier_configurations(client, db_session):
    admin, admin_headers = _create_admin(db_session)

    # 1. Config INT
    res_int = client.put(
        "/api/v1/admin/config/MAX_LOGIN_ATTEMPTS",
        json={"valeur": 5, "type": "INT", "description": "Nombre max d'essais de mot de passe"},
        headers=admin_headers,
    )
    assert res_int.status_code == 200
    data_int = res_int.json()
    assert data_int["cle"] == "MAX_LOGIN_ATTEMPTS"
    assert data_int["valeur_parsed"] == 5
    assert data_int["type"] == "INT"

    # 2. Config BOOL
    res_bool = client.put(
        "/api/v1/admin/config/FEATURE_JARVIS_ACTIVE",
        json={"valeur": True, "type": "BOOL", "description": "Activer Jarvis IA"},
        headers=admin_headers,
    )
    assert res_bool.status_code == 200
    data_bool = res_bool.json()
    assert data_bool["valeur_parsed"] is True

    # 3. Config JSON
    res_json = client.put(
        "/api/v1/admin/config/SYSTEM_NOTIFICATION_PLANS",
        json={"valeur": {"email": True, "sms": False}, "type": "JSON", "description": "Canaux d'alerte"},
        headers=admin_headers,
    )
    assert res_json.status_code == 200
    data_json = res_json.json()
    assert data_json["valeur_parsed"] == {"email": True, "sms": False}

    # AuditLog généré
    log = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_MODIFIER_CONFIG",
        AuditLog.id_ressource == data_json["id_config"]
    ).first()
    assert log is not None

def test_admin_lister_et_consulter_configurations(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="cfgview", email="cfgview@mynkap.cm")

    client.put(
        "/api/v1/admin/config/APP_THEME",
        json={"valeur": "DARK", "type": "STRING", "description": "Thème par défaut"},
        headers=admin_headers,
    )

    # 1. Lister les configurations -> 200 OK
    res_list = client.get("/api/v1/admin/config", headers=admin_headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 1
    assert any(cfg["cle"] == "APP_THEME" for cfg in items)

    # 2. Consulter une clé spécifique -> 200 OK
    res_get = client.get("/api/v1/admin/config/APP_THEME", headers=admin_headers)
    assert res_get.status_code == 200
    assert res_get.json()["valeur_parsed"] == "DARK"

    # 3. Clé introuvable -> 404 Not Found
    res_404 = client.get("/api/v1/admin/config/NON_EXISTENT_KEY", headers=admin_headers)
    assert res_404.status_code == 404

def test_admin_config_restrictions_droits(client, db_session):
    # Admin niveau 1 (Support)
    _, l1_headers = _create_admin(db_session, username="cfglevel1", email="cfglevel1@mynkap.cm", niveau_acces=1)
    
    # Client normal
    _, client_headers = _create_client(db_session)

    # 1. Admin niveau 1 peut consulter -> 200 OK
    res_l1_get = client.get("/api/v1/admin/config", headers=l1_headers)
    assert res_l1_get.status_code == 200

    # 2. Admin niveau 1 NE PEUT PAS modifier -> 403 Forbidden
    res_l1_put = client.put(
        "/api/v1/admin/config/RESTRICTED_KEY",
        json={"valeur": "test", "type": "STRING"},
        headers=l1_headers,
    )
    assert res_l1_put.status_code == 403

    # 3. Client normal NE PEUT PAS consulter -> 403 Forbidden
    res_c_get = client.get("/api/v1/admin/config", headers=client_headers)
    assert res_c_get.status_code == 403
