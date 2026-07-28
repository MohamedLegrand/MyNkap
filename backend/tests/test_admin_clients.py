from decimal import Decimal
import pytest
from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur, RefreshToken
from tests.conftest import se_connecter_avec_otp

def _create_admin(db_session, username="superadmin", email="admin@mynkap.cm", password="adminpassword123", niveau_acces=1):
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

def _register_client(client, email="client1@example.com", mot_de_passe="clientpassword123", first_name="Paul", last_name="Biya", phone="+237699999999"):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
        },
    )
    assert res.status_code == 201
    return res.json()

def test_admin_routes_forbidden_for_clients_and_guests(client, db_session):
    # 1. Accès invité sans token -> 401
    res_guest = client.get("/api/v1/admin/clients")
    assert res_guest.status_code == 401

    # 2. Accès avec token d'un simple client -> 403
    _register_client(client, "simple.client@example.com")
    login_res = se_connecter_avec_otp(client, "simple.client@example.com", "clientpassword123", db_session).json()
    client_headers = {"Authorization": f"Bearer {login_res['access_token']}"}

    res_client = client.get("/api/v1/admin/clients", headers=client_headers)
    assert res_client.status_code == 403

def test_admin_lister_et_filtrer_clients(client, db_session):
    _, admin_headers = _create_admin(db_session)
    
    _register_client(client, "alice@mynkap.cm", first_name="Alice", last_name="Nguemo", phone="+237670000001")
    _register_client(client, "bob@mynkap.cm", first_name="Bob", last_name="Mbida", phone="+237670000002")

    # Lister tous les clients
    res = client.get("/api/v1/admin/clients", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Recherche par terme "Alice"
    res_search = client.get("/api/v1/admin/clients?q=Alice", headers=admin_headers)
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["email"] == "alice@mynkap.cm"

def test_admin_obtenir_detail_client(client, db_session):
    _, admin_headers = _create_admin(db_session)
    client_data = _register_client(client, "detail.test@mynkap.cm")

    id_client = client_data["id_client"]
    res = client.get(f"/api/v1/admin/clients/{id_client}", headers=admin_headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["id_client"] == id_client
    assert detail["email"] == "detail.test@mynkap.cm"
    assert detail["nombre_comptes_financiers"] == 0

def test_admin_desactiver_et_reactiver_client_avec_audit(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="admin_status")
    client_data = _register_client(client, "suspend.test@mynkap.cm")
    id_client = client_data["id_client"]

    # Connexion du client pour générer des tokens
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "suspend.test@mynkap.cm", "mot_de_passe": "clientpassword123"}
    ).json()

    # 1. Désactivation par l'Admin
    res_deact = client.patch(
        f"/api/v1/admin/clients/{id_client}/status",
        json={"est_actif": False, "raison": "Suspicion de fraude"},
        headers=admin_headers,
    )
    assert res_deact.status_code == 200
    assert res_deact.json()["est_actif"] is False

    # Vérification de l'AuditLog
    log_deact = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_DESACTIVER_CLIENT",
        AuditLog.id_ressource == id_client
    ).first()
    assert log_deact is not None
    assert log_deact.donnees_apres["raison"] == "Suspicion de fraude"

    # Vérification du blocage de connexion du client désactivé
    login_attempt = client.post(
        "/api/v1/auth/login",
        json={"email": "suspend.test@mynkap.cm", "mot_de_passe": "clientpassword123"}
    )
    assert login_attempt.status_code == 400

    # 2. Réactivation par l'Admin
    res_react = client.patch(
        f"/api/v1/admin/clients/{id_client}/status",
        json={"est_actif": True, "raison": "Litige résolu"},
        headers=admin_headers,
    )
    assert res_react.status_code == 200
    assert res_react.json()["est_actif"] is True

    # AuditLog de réactivation
    log_react = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_ACTIVER_CLIENT",
        AuditLog.id_ressource == id_client
    ).first()
    assert log_react is not None

def test_admin_reinitialiser_mot_de_passe_client(client, db_session):
    _, admin_headers = _create_admin(db_session, username="admin_reset")
    client_data = _register_client(client, "reset.test@mynkap.cm", mot_de_passe="ancienmdp123")
    id_client = client_data["id_client"]

    # Réinitialisation par l'admin
    res_reset = client.post(
        f"/api/v1/admin/clients/{id_client}/reset-password",
        headers=admin_headers,
    )
    assert res_reset.status_code == 200
    reset_data = res_reset.json()
    assert "mot_de_passe_temporaire" in reset_data
    tmp_password = reset_data["mot_de_passe_temporaire"]

    # Connexion avec l'ancien mot de passe échoue
    fail_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset.test@mynkap.cm", "mot_de_passe": "ancienmdp123"}
    )
    assert fail_login.status_code == 400

    # Connexion avec le nouveau mot de passe temporaire réussit
    success_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset.test@mynkap.cm", "mot_de_passe": tmp_password}
    )
    assert success_login.status_code == 200

    # Vérification AuditLog
    log_reset = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_REINITIALISER_MDP_CLIENT",
        AuditLog.id_ressource == id_client
    ).first()
    assert log_reset is not None
