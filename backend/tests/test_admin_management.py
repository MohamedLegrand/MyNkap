import pytest
from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur

def _create_admin(db_session, username="superadmin", email="superadmin@mynkap.cm", password="adminpassword123", niveau_acces=3):
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

def test_connexion_admin_via_login_reel(client, db_session):
    # Passe par le vrai endpoint /auth/login (pas de JWT fabriqué à la main) :
    # seul chemin qui exerce réellement creer_refresh_token() et aurait
    # détecté la violation de contrainte étrangère Postgres sur
    # refresh_tokens.id_client (celle-ci pointait vers clients.id_client,
    # or un Administrateur n'a pas de ligne dans `clients`).
    _create_admin(db_session, username="loginreel", email="loginreel@mynkap.cm", password="adminpassword123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "loginreel@mynkap.cm", "mot_de_passe": "adminpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Le token émis doit permettre d'accéder à une route admin protégée
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    res_admins = client.get("/api/v1/admin/admins", headers=headers)
    assert res_admins.status_code == 200

def test_superadmin_creer_nouvel_admin(client, db_session):
    superadmin, superadmin_headers = _create_admin(db_session, username="super1", email="super1@mynkap.cm", niveau_acces=3)

    response = client.post(
        "/api/v1/admin/admins",
        json={
            "email": "moderateur@mynkap.cm",
            "username": "mod1",
            "mot_de_passe": "modpassword123",
            "niveau_acces": 2,
        },
        headers=superadmin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "moderateur@mynkap.cm"
    assert data["username"] == "mod1"
    assert data["niveau_acces"] == 2
    assert data["est_actif"] is True

    # Vérification de l'AuditLog
    log = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_CREER_ADMIN",
        AuditLog.id_ressource == data["id_administrateur"]
    ).first()
    assert log is not None
    assert log.donnees_apres["username"] == "mod1"

def test_admin_creer_admin_doublon_email_ou_username(client, db_session):
    _, superadmin_headers = _create_admin(db_session, username="super2", email="super2@mynkap.cm")

    client.post(
        "/api/v1/admin/admins",
        json={
            "email": "unique@mynkap.cm",
            "username": "uniqueuser",
            "mot_de_passe": "password123",
            "niveau_acces": 1,
        },
        headers=superadmin_headers,
    )

    # 1. Doublon Email -> 400 Bad Request
    res_dup_email = client.post(
        "/api/v1/admin/admins",
        json={
            "email": "unique@mynkap.cm",
            "username": "otheruser",
            "mot_de_passe": "password123",
            "niveau_acces": 1,
        },
        headers=superadmin_headers,
    )
    assert res_dup_email.status_code == 400

    # 2. Doublon Username -> 400 Bad Request
    res_dup_user = client.post(
        "/api/v1/admin/admins",
        json={
            "email": "other@mynkap.cm",
            "username": "uniqueuser",
            "mot_de_passe": "password123",
            "niveau_acces": 1,
        },
        headers=superadmin_headers,
    )
    assert res_dup_user.status_code == 400

def test_restrictions_creation_par_niveau_acces(client, db_session):
    # Admin niveau 1 (Support)
    _, level1_headers = _create_admin(db_session, username="agent1", email="agent1@mynkap.cm", niveau_acces=1)
    
    # Admin niveau 2 (Modérateur)
    _, level2_headers = _create_admin(db_session, username="mod2", email="mod2@mynkap.cm", niveau_acces=2)

    # 1. Niveau 1 essaie de créer un admin -> 403 Forbidden
    res_l1 = client.post(
        "/api/v1/admin/admins",
        json={"email": "new1@mynkap.cm", "username": "new1", "mot_de_passe": "password123", "niveau_acces": 1},
        headers=level1_headers,
    )
    assert res_l1.status_code == 403

    # 2. Niveau 2 essaie de créer un Superadmin (niveau 3) -> 403 Forbidden
    res_l2_super = client.post(
        "/api/v1/admin/admins",
        json={"email": "newsuper@mynkap.cm", "username": "newsuper", "mot_de_passe": "password123", "niveau_acces": 3},
        headers=level2_headers,
    )
    assert res_l2_super.status_code == 403

    # 3. Niveau 2 crée un Niveau 1 -> 201 Created
    res_l2_ok = client.post(
        "/api/v1/admin/admins",
        json={"email": "newagent@mynkap.cm", "username": "newagent", "mot_de_passe": "password123", "niveau_acces": 1},
        headers=level2_headers,
    )
    assert res_l2_ok.status_code == 201

def test_superadmin_modifier_niveau_acces_et_protection_dernier_superadmin(client, db_session):
    superadmin, superadmin_headers = _create_admin(db_session, username="onlysuper", email="onlysuper@mynkap.cm", niveau_acces=3)

    # 1. Création d'un admin niveau 1
    agent = client.post(
        "/api/v1/admin/admins",
        json={"email": "agent.promo@mynkap.cm", "username": "agentpromo", "mot_de_passe": "password123", "niveau_acces": 1},
        headers=superadmin_headers,
    ).json()

    # Promotion de niveau 1 à niveau 2 par le Superadmin -> 200 OK
    res_promo = client.patch(
        f"/api/v1/admin/admins/{agent['id_administrateur']}/level",
        json={"niveau_acces": 2},
        headers=superadmin_headers,
    )
    assert res_promo.status_code == 200
    assert res_promo.json()["niveau_acces"] == 2

    # 2. Tentative de rétrogradation du SEUL Superadmin actif -> 400 Bad Request
    res_demote_last = client.patch(
        f"/api/v1/admin/admins/{superadmin.id_administrateur}/level",
        json={"niveau_acces": 2},
        headers=superadmin_headers,
    )
    assert res_demote_last.status_code == 400
    assert "dernier Superadmin" in res_demote_last.json()["detail"]

def test_interdiction_auto_suspension_et_protection_dernier_superadmin_statut(client, db_session):
    superadmin1, headers1 = _create_admin(db_session, username="superonly", email="superonly@mynkap.cm", niveau_acces=3)

    # 1. Tentative de désactiver son propre compte -> 400 Bad Request
    res_self_deact = client.patch(
        f"/api/v1/admin/admins/{superadmin1.id_administrateur}/status",
        json={"est_actif": False, "raison": "Test auto suspension"},
        headers=headers1,
    )
    assert res_self_deact.status_code == 400
    assert "propre compte" in res_self_deact.json()["detail"]

    # 2. Création d'un 2ème Superadmin
    superadmin2_data = client.post(
        "/api/v1/admin/admins",
        json={"email": "supertwo@mynkap.cm", "username": "supertwo", "mot_de_passe": "password123", "niveau_acces": 3},
        headers=headers1,
    ).json()

    # Superadmin 1 désactive Superadmin 2 -> 200 OK
    res_deact_s2 = client.patch(
        f"/api/v1/admin/admins/{superadmin2_data['id_administrateur']}/status",
        json={"est_actif": False, "raison": "Départ de l'entreprise"},
        headers=headers1,
    )
    assert res_deact_s2.status_code == 200
    assert res_deact_s2.json()["est_actif"] is False

    # AuditLog de désactivation
    log_deact = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_DESACTIVER_ADMIN",
        AuditLog.id_ressource == superadmin2_data["id_administrateur"]
    ).first()
    assert log_deact is not None

    # Maintenant Superadmin 2 est inactif. Superadmin 1 est à nouveau le SEUL Superadmin actif.
    # Superadmin 1 essaie de désactiver Superadmin 2 à nouveau (déjà inactif) ou de se désactiver -> Bloqué
    # Crée un 3ème admin temporaire pour tester la tentative d'impact sur le dernier superadmin actif :
    superadmin2_token = create_access_token(subject=superadmin2_data["id_administrateur"])
    headers2 = {"Authorization": f"Bearer {superadmin2_token}"}

    # Superadmin 2 (inactif) essaie d'accéder à l'API -> 400 Bad Request ("Compte utilisateur désactivé")
    res_inactive_access = client.get("/api/v1/admin/admins", headers=headers2)
    assert res_inactive_access.status_code == 400
