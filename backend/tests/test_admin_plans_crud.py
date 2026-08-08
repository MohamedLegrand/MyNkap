from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur, Client
from app.modules.plans.models import Abonnement, Plan


def _create_admin(db_session, username="plancrudadmin", email="plancrudadmin@mynkap.cm", password="adminpassword123", niveau_acces=2):
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


def _create_client(db_session, email="clientplancrud@mynkap.cm", password="clientpassword123"):
    c = Client(
        email=email,
        first_name="Jean",
        last_name="Biyick",
        phone="+237698888888",
        mot_de_passe=get_password_hash(password),
        est_actif=True,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    token = create_access_token(subject=c.id_client)
    return c, {"Authorization": f"Bearer {token}"}


def test_admin_cree_modifie_et_supprime_un_plan(client, db_session):
    _, headers = _create_admin(db_session)

    # 1. Création
    res_create = client.post(
        "/api/v1/admin/plans",
        json={
            "nom": "entreprise",
            "prix_mensuel": 15000,
            "prix_annuel": 150000,
            "devise": "XAF",
            "acces_dettes": True,
            "acces_jarvis": True,
        },
        headers=headers,
    )
    assert res_create.status_code == 201
    data = res_create.json()
    assert data["nom"] == "ENTREPRISE"
    assert data["acces_dettes"] is True
    assert data["acces_epargne"] is False
    id_plan = data["id_plan"]

    log_create = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_CREER_PLAN", AuditLog.id_ressource == id_plan
    ).first()
    assert log_create is not None

    # 2. Doublon de nom refusé
    res_doublon = client.post(
        "/api/v1/admin/plans",
        json={"nom": "ENTREPRISE", "prix_mensuel": 1, "prix_annuel": 1},
        headers=headers,
    )
    assert res_doublon.status_code == 409

    # 3. Modification (prix + accès)
    res_update = client.put(
        f"/api/v1/admin/plans/{id_plan}",
        json={"prix_mensuel": 20000, "acces_epargne": True},
        headers=headers,
    )
    assert res_update.status_code == 200
    data_upd = res_update.json()
    assert float(data_upd["prix_mensuel"]) == 20000
    assert data_upd["acces_epargne"] is True
    assert data_upd["acces_dettes"] is True  # inchangé

    log_update = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_MODIFIER_PLAN", AuditLog.id_ressource == id_plan
    ).first()
    assert log_update is not None

    # 4. Suppression
    res_delete = client.delete(f"/api/v1/admin/plans/{id_plan}", headers=headers)
    assert res_delete.status_code == 204

    assert db_session.query(Plan).filter(Plan.id_plan == id_plan).first() is None
    log_delete = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_SUPPRIMER_PLAN", AuditLog.id_ressource == id_plan
    ).first()
    assert log_delete is not None


def test_admin_ne_peut_pas_renommer_ou_supprimer_un_plan_systeme(client, db_session):
    _, headers = _create_admin(db_session, username="planl2", email="planl2@mynkap.cm")

    plan_gratuit = db_session.query(Plan).filter(Plan.nom == "GRATUIT").first()
    assert plan_gratuit is not None

    # Renommer un plan système -> refusé
    res_rename = client.put(
        f"/api/v1/admin/plans/{plan_gratuit.id_plan}",
        json={"nom": "GRATUIT_V2"},
        headers=headers,
    )
    assert res_rename.status_code == 400

    # Modifier ses tarifs/accès reste autorisé
    res_update = client.put(
        f"/api/v1/admin/plans/{plan_gratuit.id_plan}",
        json={"acces_analyse": True},
        headers=headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["nom"] == "GRATUIT"
    assert res_update.json()["acces_analyse"] is True

    # Suppression d'un plan système -> refusé
    res_delete = client.delete(f"/api/v1/admin/plans/{plan_gratuit.id_plan}", headers=headers)
    assert res_delete.status_code == 400


def test_admin_ne_peut_pas_supprimer_un_plan_avec_abonnes(client, db_session):
    _, headers = _create_admin(db_session, username="planl2b", email="planl2b@mynkap.cm")
    user_c, _ = _create_client(db_session)

    res_create = client.post(
        "/api/v1/admin/plans",
        json={"nom": "STARTUP", "prix_mensuel": 5000, "prix_annuel": 50000},
        headers=headers,
    )
    id_plan = res_create.json()["id_plan"]

    abonnement = Abonnement(id_client=user_c.id_client, id_plan=id_plan, statut="ACTIF")
    db_session.add(abonnement)
    db_session.commit()

    res_delete = client.delete(f"/api/v1/admin/plans/{id_plan}", headers=headers)
    assert res_delete.status_code == 409


def test_admin_plans_crud_restrictions_droits(client, db_session):
    # Admin niveau 1 (Support) : lecture OK, écriture refusée
    _, l1_headers = _create_admin(db_session, username="planl1crud", email="planl1crud@mynkap.cm", niveau_acces=1)
    # Client normal : tout refusé
    _, c_headers = _create_client(db_session, email="normalplancrud@mynkap.cm")

    res_l1_list = client.get("/api/v1/admin/plans", headers=l1_headers)
    assert res_l1_list.status_code == 200

    res_l1_create = client.post(
        "/api/v1/admin/plans",
        json={"nom": "XX", "prix_mensuel": 1, "prix_annuel": 1},
        headers=l1_headers,
    )
    assert res_l1_create.status_code == 403

    res_c_list = client.get("/api/v1/admin/plans", headers=c_headers)
    assert res_c_list.status_code == 403
