from datetime import datetime, timedelta

from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur, Client


def _register_and_login(client, email="avis.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Awa",
            "last_name": "Biyick",
            "phone": "+237600000000",
        },
    )
    access_token = client.post(
        "/api/v1/auth/login", json={"email": email, "mot_de_passe": mot_de_passe}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _create_admin(db_session, username="avisadmin", email="avisadmin@mynkap.cm", niveau_acces=2):
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


def test_avis_publics_est_accessible_sans_authentification(client):
    reponse = client.get("/api/v1/avis/publics")
    assert reponse.status_code == 200
    assert reponse.json() == []


def test_mon_avis_est_null_avant_toute_soumission(client):
    headers = _register_and_login(client, "avis.vide@example.com")
    reponse = client.get("/api/v1/avis/moi", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json() is None


def test_creer_avis_puis_le_consulter(client):
    headers = _register_and_login(client, "avis.creation@example.com")
    reponse = client.post(
        "/api/v1/avis",
        json={"note": 5, "commentaire": "Application très pratique pour suivre mon Mobile Money."},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "EN_ATTENTE"
    assert body["note"] == 5

    mon_avis = client.get("/api/v1/avis/moi", headers=headers).json()
    assert mon_avis["id_avis"] == body["id_avis"]

    # Pas encore publié : invisible sur la landing page.
    assert client.get("/api/v1/avis/publics").json() == []


def test_creer_un_deuxieme_avis_est_refuse(client):
    headers = _register_and_login(client, "avis.doublon@example.com")
    client.post("/api/v1/avis", json={"note": 4, "commentaire": "Bien."}, headers=headers)

    reponse = client.post("/api/v1/avis", json={"note": 3, "commentaire": "Encore un."}, headers=headers)
    assert reponse.status_code == 409


def test_creer_avis_note_hors_bornes_est_refuse(client):
    headers = _register_and_login(client, "avis.bornes@example.com")
    reponse = client.post("/api/v1/avis", json={"note": 6, "commentaire": "Trop bien."}, headers=headers)
    assert reponse.status_code == 422


def test_moderer_avis_niveau1_est_refuse(client, db_session):
    headers = _register_and_login(client, "avis.moderation.refus@example.com")
    id_avis = client.post("/api/v1/avis", json={"note": 5, "commentaire": "Top."}, headers=headers).json()["id_avis"]

    _, admin_headers = _create_admin(db_session, niveau_acces=1)
    reponse = client.patch(f"/api/v1/admin/avis/{id_avis}", json={"statut": "PUBLIE"}, headers=admin_headers)
    assert reponse.status_code == 403


def test_moderer_avis_publie_apparait_sur_la_landing_page(client, db_session):
    headers = _register_and_login(client, "avis.publication@example.com")
    id_avis = client.post(
        "/api/v1/avis", json={"note": 5, "commentaire": "Je gère enfin mes tontines facilement."}, headers=headers
    ).json()["id_avis"]

    _, admin_headers = _create_admin(db_session, niveau_acces=2)
    reponse = client.patch(f"/api/v1/admin/avis/{id_avis}", json={"statut": "PUBLIE"}, headers=admin_headers)
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "PUBLIE"

    publics = client.get("/api/v1/avis/publics").json()
    assert len(publics) == 1
    assert publics[0]["auteur"] == "Awa B."
    assert "@" not in publics[0]["auteur"]

    log = db_session.query(AuditLog).filter(AuditLog.action == "ADMIN_MODERER_AVIS").first()
    assert log is not None
    assert log.id_ressource == id_avis


def test_avis_publie_sans_photo_de_profil_a_un_avatar_nul(client, db_session):
    headers = _register_and_login(client, "avis.sans.photo@example.com")
    id_avis = client.post(
        "/api/v1/avis", json={"note": 5, "commentaire": "Nickel."}, headers=headers
    ).json()["id_avis"]

    _, admin_headers = _create_admin(db_session, niveau_acces=2, username="avisadmin2", email="avisadmin2@mynkap.cm")
    client.patch(f"/api/v1/admin/avis/{id_avis}", json={"statut": "PUBLIE"}, headers=admin_headers)

    publics = client.get("/api/v1/avis/publics").json()
    assert publics[0]["avatar"] is None


def test_avis_publie_reprend_la_photo_de_profil_du_client(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _register_and_login(client, "avis.avec.photo@example.com")
    client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("avatar.png", b"contenu-image-factice", "image/png")},
    )
    id_avis = client.post(
        "/api/v1/avis", json={"note": 5, "commentaire": "Nickel avec photo."}, headers=headers
    ).json()["id_avis"]

    _, admin_headers = _create_admin(db_session, niveau_acces=2, username="avisadmin3", email="avisadmin3@mynkap.cm")
    client.patch(f"/api/v1/admin/avis/{id_avis}", json={"statut": "PUBLIE"}, headers=admin_headers)

    publics = client.get("/api/v1/avis/publics").json()
    assert publics[0]["avatar"] is not None
    assert publics[0]["avatar"].startswith(f"{settings.BACKEND_URL}/avatars/")


def test_moderer_avis_rejete_reste_invisible(client, db_session):
    headers = _register_and_login(client, "avis.rejet@example.com")
    id_avis = client.post("/api/v1/avis", json={"note": 1, "commentaire": "Mauvaise expérience."}, headers=headers).json()["id_avis"]

    _, admin_headers = _create_admin(db_session, niveau_acces=3)
    reponse = client.patch(f"/api/v1/admin/avis/{id_avis}", json={"statut": "REJETE"}, headers=admin_headers)
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "REJETE"

    assert client.get("/api/v1/avis/publics").json() == []


def test_lister_avis_admin_avec_filtre_statut(client, db_session):
    headers_a = _register_and_login(client, "avis.liste.a@example.com")
    headers_b = _register_and_login(client, "avis.liste.b@example.com")
    client.post("/api/v1/avis", json={"note": 5, "commentaire": "A"}, headers=headers_a)
    id_avis_b = client.post("/api/v1/avis", json={"note": 2, "commentaire": "B"}, headers=headers_b).json()["id_avis"]

    _, admin_headers = _create_admin(db_session, niveau_acces=2)
    client.patch(f"/api/v1/admin/avis/{id_avis_b}", json={"statut": "PUBLIE"}, headers=admin_headers)

    reponse = client.get("/api/v1/admin/avis?statut=EN_ATTENTE", headers=admin_headers)
    assert reponse.status_code == 200
    body = reponse.json()
    assert body["total"] == 1
    assert body["items"][0]["commentaire"] == "A"


def _vieillir_le_compte(db_session, id_client, jours=15):
    """Recule artificiellement date_creation pour simuler un client ancien
    — doit_demander_avis exige 14 jours d'ancienneté minimum."""
    c = db_session.query(Client).filter(Client.id_client == id_client).first()
    c.date_creation = datetime.utcnow() - timedelta(days=jours)
    db_session.commit()


def _id_client_courant(db_session, email):
    return db_session.query(Client).filter(Client.email == email).first().id_client


def test_invitation_avis_refusee_si_compte_recent(client, db_session):
    headers = _register_and_login(client, "avis.invitation.recent@example.com")
    reponse = client.get("/api/v1/avis/invitation", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["demander"] is False


def test_invitation_avis_acceptee_apres_anciennete_suffisante(client, db_session):
    email = "avis.invitation.ancien@example.com"
    headers = _register_and_login(client, email)
    _vieillir_le_compte(db_session, _id_client_courant(db_session, email))

    reponse = client.get("/api/v1/avis/invitation", headers=headers)
    assert reponse.json()["demander"] is True


def test_invitation_avis_refusee_si_avis_deja_soumis(client, db_session):
    email = "avis.invitation.deja@example.com"
    headers = _register_and_login(client, email)
    _vieillir_le_compte(db_session, _id_client_courant(db_session, email))
    client.post("/api/v1/avis", json={"note": 4, "commentaire": "Déjà donné."}, headers=headers)

    reponse = client.get("/api/v1/avis/invitation", headers=headers)
    assert reponse.json()["demander"] is False


def test_reporter_avis_repousse_linvitation(client, db_session):
    email = "avis.report@example.com"
    headers = _register_and_login(client, email)
    _vieillir_le_compte(db_session, _id_client_courant(db_session, email))
    assert client.get("/api/v1/avis/invitation", headers=headers).json()["demander"] is True

    reponse = client.post("/api/v1/avis/reporter", headers=headers)
    assert reponse.status_code == 204

    assert client.get("/api/v1/avis/invitation", headers=headers).json()["demander"] is False

    c = db_session.query(Client).filter(Client.email == email).first()
    assert c.prochaine_invitation_avis is not None
    assert c.prochaine_invitation_avis > datetime.utcnow() + timedelta(days=6)
