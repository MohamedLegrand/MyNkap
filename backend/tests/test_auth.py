from app.modules.auth import services as auth_services
from app.modules.auth.models import Client, Utilisateur
from app.modules.notifications.models import Notification
from tests.conftest import se_connecter_avec_otp


def _register_payload(**overrides):
    payload = {
        "email": "jean.dupont@example.com",
        "mot_de_passe": "motdepasse123",
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+237600000000",
    }
    payload.update(overrides)
    return payload


def test_register_creates_client_with_default_profile(client):
    response = client.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jean.dupont@example.com"
    assert body["profile"]["devise"] == "XAF"
    assert body["profile"]["langue"] == "FR"


def test_register_rejects_duplicate_email(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    response = client.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 400


def test_login_step1_avec_identifiants_corrects_declenche_un_otp(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["otp_requis"] is True
    assert "access_token" not in body

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_client.otp_code is not None
    assert len(db_client.otp_code) == 6
    assert db_client.otp_expiration is not None


def test_login_with_wrong_password_is_rejected(client):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
    )

    assert response.status_code == 400


def test_verify_otp_avec_code_correct_renvoie_les_jetons(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session)

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user_type"] == "client"


def test_verify_otp_avec_code_incorrect_est_rejete(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "jean.dupont@example.com", "code": "000000"},
    )
    assert response.status_code == 400


def test_verify_otp_est_a_usage_unique(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    code = db_client.otp_code

    premiere_verification = client.post(
        "/api/v1/auth/verify-otp", json={"email": "jean.dupont@example.com", "code": code}
    )
    assert premiere_verification.status_code == 200

    # Rejouer le même code une seconde fois échoue (déjà invalidé en base)
    reponse_rejouee = client.post(
        "/api/v1/auth/verify-otp", json={"email": "jean.dupont@example.com", "code": code}
    )
    assert reponse_rejouee.status_code == 400


def test_verify_otp_expire_est_rejete(client, db_session):
    from datetime import datetime, timedelta

    client.post("/api/v1/auth/register", json=_register_payload())
    client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    code = db_client.otp_code
    db_client.otp_expiration = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "jean.dupont@example.com", "code": code},
    )
    assert response.status_code == 400


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_client_with_valid_token(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session).json()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "jean.dupont@example.com"


def test_refresh_token_issues_new_access_token(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session).json()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_token_tourne_et_invalide_lancien(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session).json()
    ancien_refresh_token = tokens["refresh_token"]

    premiere_reponse = client.post("/api/v1/auth/refresh", json={"refresh_token": ancien_refresh_token})
    assert premiere_reponse.status_code == 200
    nouveau_refresh_token = premiere_reponse.json()["refresh_token"]

    # Le jeton renvoyé n'est jamais le même : rotation à chaque appel.
    assert nouveau_refresh_token != ancien_refresh_token

    # Rejouer l'ancien jeton (déjà tourné) échoue désormais.
    reponse_rejouee = client.post("/api/v1/auth/refresh", json={"refresh_token": ancien_refresh_token})
    assert reponse_rejouee.status_code == 401

    # Le nouveau jeton, lui, fonctionne toujours.
    reponse_nouveau = client.post("/api/v1/auth/refresh", json={"refresh_token": nouveau_refresh_token})
    assert reponse_nouveau.status_code == 200


def test_refresh_token_nest_jamais_stocke_en_clair(client, db_session):
    from app.modules.auth.models import RefreshToken

    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session).json()

    db_token = db_session.query(RefreshToken).order_by(RefreshToken.id_refresh_token.desc()).first()
    assert db_token.token_hash != tokens["refresh_token"]
    assert auth_services._hasher_token(tokens["refresh_token"]) == db_token.token_hash


def test_logout_revokes_refresh_token(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session).json()
    refresh_token = tokens["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_forgot_password_generates_a_reset_token_for_existing_email(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/forgot-password", json={"email": "jean.dupont@example.com"}
    )
    assert response.status_code == 200

    db_client = db_session.query(Client).filter(Client.email == "jean.dupont@example.com").first()
    assert db_client.reset_password_token is not None
    assert db_client.reset_password_expires is not None


def test_forgot_password_renvoie_200_meme_pour_un_email_inconnu(client):
    # Message générique volontaire (voir auth/router.py) pour éviter le
    # dénombrement d'utilisateurs : ne doit jamais révéler si l'email existe.
    response = client.post(
        "/api/v1/auth/forgot-password", json={"email": "inconnu@example.com"}
    )
    assert response.status_code == 200


def test_reset_password_avec_jeton_valide_permet_de_se_reconnecter(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    client.post("/api/v1/auth/forgot-password", json={"email": "jean.dupont@example.com"})

    db_client = db_session.query(Client).filter(Client.email == "jean.dupont@example.com").first()
    reset_token = db_client.reset_password_token

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "nouveau_mot_de_passe": "nouveaumotdepasse456"},
    )
    assert response.status_code == 200

    # L'ancien mot de passe ne fonctionne plus
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )
    assert old_login.status_code == 400

    # Le nouveau mot de passe fonctionne (étape 1 : déclenche l'envoi de l'OTP)
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "nouveaumotdepasse456"},
    )
    assert new_login.status_code == 200


def test_reset_password_avec_jeton_invalide_est_rejete(client):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "jeton-inexistant", "nouveau_mot_de_passe": "peuimporte123"},
    )
    assert response.status_code == 400


def test_reset_password_avec_jeton_expire_est_rejete(client, db_session):
    from datetime import datetime, timedelta

    client.post("/api/v1/auth/register", json=_register_payload())
    client.post("/api/v1/auth/forgot-password", json={"email": "jean.dupont@example.com"})

    db_client = db_session.query(Client).filter(Client.email == "jean.dupont@example.com").first()
    reset_token = db_client.reset_password_token
    db_client.reset_password_expires = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "nouveau_mot_de_passe": "peuimporte123"},
    )
    assert response.status_code == 400


# --- Connexion via Google (Google Identity Services) ---

def _mocker_id_token_google(monkeypatch, email="jean.dupont@example.com"):
    monkeypatch.setattr(
        auth_services,
        "_verifier_id_token_google",
        lambda id_token_str: {"email": email, "email_verified": True},
    )


def test_login_google_pour_un_compte_existant_declenche_un_otp(client, db_session, monkeypatch):
    client.post("/api/v1/auth/register", json=_register_payload())
    _mocker_id_token_google(monkeypatch)

    response = client.post("/api/v1/auth/google", json={"id_token": "faux-jeton-google"})

    assert response.status_code == 200
    assert response.json()["otp_requis"] is True

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_client.otp_code is not None


def test_login_google_pour_un_compte_inexistant_est_rejete(client, monkeypatch):
    _mocker_id_token_google(monkeypatch, email="personne@example.com")

    response = client.post("/api/v1/auth/google", json={"id_token": "faux-jeton-google"})
    assert response.status_code == 404


def test_login_google_avec_jeton_invalide_est_rejete(client, monkeypatch):
    def leve_erreur(id_token_str):
        raise ValueError("Jeton invalide")

    monkeypatch.setattr(auth_services, "_verifier_id_token_google", leve_erreur)

    response = client.post("/api/v1/auth/google", json={"id_token": "jeton-corrompu"})
    assert response.status_code == 400


def test_login_google_complete_le_meme_flux_otp_que_le_mot_de_passe(client, db_session, monkeypatch):
    client.post("/api/v1/auth/register", json=_register_payload())
    _mocker_id_token_google(monkeypatch)
    client.post("/api/v1/auth/google", json={"id_token": "faux-jeton-google"})

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    code = db_client.otp_code

    reponse = client.post(
        "/api/v1/auth/verify-otp", json={"email": "jean.dupont@example.com", "code": code}
    )
    assert reponse.status_code == 200
    assert reponse.json()["access_token"]


# --- Tentatives de connexion échouées & notifications ---

def test_connexion_reussie_cree_une_notification_client(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session).json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    notifs = client.get("/api/v1/notifications", headers=headers).json()
    assert any(n["type"] == "CONNEXION_REUSSIE" for n in notifs)


def test_plusieurs_mots_de_passe_incorrects_notifient_le_client_une_seule_fois(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    for _ in range(auth_services.SEUIL_ALERTE_TENTATIVES + 2):
        client.post(
            "/api/v1/auth/login",
            json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
        )

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_client.tentatives_echouees == auth_services.SEUIL_ALERTE_TENTATIVES + 2
    assert db_client.alerte_tentatives_envoyee is True

    notifs_tentatives = (
        db_session.query(Notification)
        .filter(Notification.id_utilisateur == db_client.id_utilisateur, Notification.type == "TENTATIVES_ECHOUEES")
        .all()
    )
    # Une seule notification malgré les échecs supplémentaires après le seuil.
    assert len(notifs_tentatives) == 1


def test_une_connexion_reussie_reinitialise_le_compteur_de_tentatives(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    for _ in range(auth_services.SEUIL_ALERTE_TENTATIVES):
        client.post(
            "/api/v1/auth/login",
            json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
        )

    se_connecter_avec_otp(client, "jean.dupont@example.com", "motdepasse123", db_session)

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_client.tentatives_echouees == 0
    assert db_client.alerte_tentatives_envoyee is False
