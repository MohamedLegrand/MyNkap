from app.modules.auth import services as auth_services
from app.modules.auth.models import Client, Utilisateur
from app.modules.notifications.models import Notification
from tests.conftest import se_connecter


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


def test_register_creates_client_with_default_profile(client, db_session):
    """
    /auth/register ne renvoie pas le client directement : un code de
    vérification part par e-mail et la réponse ne contient que
    otp_requis/message/expires_in — voir test_register_declenche_un_otp.
    Le client et son profil par défaut existent bien en base dès cet appel,
    avant même toute vérification OTP.
    """
    response = client.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["otp_requis"] is True
    assert body["expires_in"] == 300

    db_client = db_session.query(Client).filter(Client.email == "jean.dupont@example.com").first()
    assert db_client is not None
    assert db_client.profile.devise == "XAF"
    assert db_client.profile.langue == "FR"
    assert db_client.email_verifie is False


def test_register_declenche_un_otp(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    db_utilisateur = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_utilisateur.otp_code is not None
    assert db_utilisateur.otp_expiration is not None


def test_verifier_otp_apres_inscription_confirme_lemail_sans_ouvrir_de_session(client, db_session):
    """
    /auth/verify-otp ne sert plus qu'à confirmer l'e-mail à l'inscription :
    il n'émet plus de jetons — le client doit se connecter séparément via
    /auth/login (voir test_login_avec_identifiants_corrects_renvoie_les_jetons).
    """
    client.post("/api/v1/auth/register", json=_register_payload())

    db_utilisateur = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    code = db_utilisateur.otp_code

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "jean.dupont@example.com", "code": code},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert body["message"]

    db_session.refresh(db_utilisateur)
    assert db_utilisateur.email_verifie is True


def _verifier_email(client, db_session, email="jean.dupont@example.com"):
    """Lit le code OTP directement en base et le vérifie via /auth/verify-otp
    — même principe que _register_client dans test_admin_clients.py."""
    db_utilisateur = db_session.query(Utilisateur).filter(Utilisateur.email == email).first()
    reponse = client.post(
        "/api/v1/auth/verify-otp", json={"email": email, "code": db_utilisateur.otp_code}
    )
    assert reponse.status_code == 200
    db_session.refresh(db_utilisateur)


def test_register_renvoie_un_nouveau_code_si_le_compte_nest_pas_encore_verifie(client, db_session):
    """
    Voir auth.router.register : ré-inscrire un e-mail déjà utilisé mais
    jamais vérifié ne recrée pas de doublon, renvoie simplement un nouveau
    code — c'est ce que rappelle le bouton "renvoyer le code" du frontend
    (OtpVerificationStep.onResend), indispensable maintenant que la
    connexion exige l'e-mail vérifié (voir EmailNonVerifieError).
    """
    client.post("/api/v1/auth/register", json=_register_payload())
    db_utilisateur = db_session.query(Utilisateur).filter(
        Utilisateur.email == "jean.dupont@example.com"
    ).first()
    premier_code = db_utilisateur.otp_code

    response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201
    assert response.json()["otp_requis"] is True

    # Un seul compte, avec un nouveau code — jamais un doublon.
    assert db_session.query(Utilisateur).filter(
        Utilisateur.email == "jean.dupont@example.com"
    ).count() == 1
    db_session.refresh(db_utilisateur)
    assert db_utilisateur.otp_code != premier_code


def test_register_rejects_duplicate_email_une_fois_verifie(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    _verifier_email(client, db_session)

    response = client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 400


def test_login_avant_verification_de_lemail_est_refuse(client):
    """
    Le cœur du correctif : des identifiants corrects ne suffisent pas tant
    que l'e-mail n'a jamais été vérifié — sans ce contrôle, l'étape OTP de
    l'inscription ne vérifiait rien en pratique (voir EmailNonVerifieError).
    """
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    assert response.status_code == 403
    assert "vérifi" in response.json()["detail"].lower()


def test_login_avec_identifiants_corrects_renvoie_les_jetons(client, db_session):
    """
    Une fois l'e-mail vérifié (voir /auth/verify-otp), la connexion n'a
    plus d'étape OTP supplémentaire : /auth/login émet directement les
    jetons de session.
    """
    client.post("/api/v1/auth/register", json=_register_payload())
    _verifier_email(client, db_session)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user_type"] == "client"


def test_login_with_wrong_password_is_rejected(client):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
    )

    assert response.status_code == 400


def test_verify_otp_avec_code_incorrect_est_rejete(client):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "jean.dupont@example.com", "code": "000000"},
    )
    assert response.status_code == 400


def test_verify_otp_est_a_usage_unique(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

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
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "jean.dupont@example.com"


def test_refresh_token_issues_new_access_token(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_token_tourne_et_invalide_lancien(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
    ancien_refresh_token = tokens["refresh_token"]

    premiere_reponse = client.post("/api/v1/auth/refresh", json={"refresh_token": ancien_refresh_token})
    assert premiere_reponse.status_code == 200
    nouveau_refresh_token = premiere_reponse.json()["refresh_token"]

    # Le jeton renvoyé n'est jamais le même : rotation à chaque appel.
    assert nouveau_refresh_token != ancien_refresh_token

    # Rejouer l'ancien jeton (déjà tourné) échoue.
    reponse_rejouee = client.post("/api/v1/auth/refresh", json={"refresh_token": ancien_refresh_token})
    assert reponse_rejouee.status_code == 401

    # Ce rejeu vient d'avoir lieu (bien avant FENETRE_GRACE_REUTILISATION) :
    # traité comme une simple retentative réseau bénigne, pas comme un vol
    # (voir services.valider_refresh_token) — le jeton légitime tout juste
    # émis par la rotation ci-dessus continue donc de fonctionner.
    reponse_nouveau = client.post("/api/v1/auth/refresh", json={"refresh_token": nouveau_refresh_token})
    assert reponse_nouveau.status_code == 200


def test_reutilisation_tardive_refresh_token_revoque_toutes_les_sessions(client, db_session):
    """Passé la fenêtre de grâce (voir services.FENETRE_GRACE_REUTILISATION),
    la réutilisation d'un jeton révoqué n'a plus de justification bénigne :
    toutes les sessions du client sont révoquées par précaution et il est
    notifié — vérifié ici en reculant artificiellement date_revocation en
    base, pour ne pas dépendre d'un vrai sommeil de plusieurs secondes dans
    le test."""
    from datetime import timedelta
    from app.modules.auth.models import RefreshToken
    from app.modules.auth import services as auth_services

    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
    ancien_refresh_token = tokens["refresh_token"]

    premiere_reponse = client.post("/api/v1/auth/refresh", json={"refresh_token": ancien_refresh_token})
    nouveau_refresh_token = premiere_reponse.json()["refresh_token"]

    ancien_en_base = (
        db_session.query(RefreshToken)
        .filter(RefreshToken.token_hash == auth_services._hasher_token(ancien_refresh_token))
        .first()
    )
    ancien_en_base.date_revocation -= (auth_services.FENETRE_GRACE_REUTILISATION + timedelta(seconds=5))
    db_session.commit()

    reponse_rejouee = client.post("/api/v1/auth/refresh", json={"refresh_token": ancien_refresh_token})
    assert reponse_rejouee.status_code == 401

    # Le jeton légitime, lui, a été révoqué par précaution.
    reponse_nouveau = client.post("/api/v1/auth/refresh", json={"refresh_token": nouveau_refresh_token})
    assert reponse_nouveau.status_code == 401

    utilisateur = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    notif = (
        db_session.query(Notification)
        .filter(Notification.id_utilisateur == utilisateur.id_utilisateur, Notification.type == "SECURITE_SESSION_COMPROMISE")
        .first()
    )
    assert notif is not None


def test_refresh_token_nest_jamais_stocke_en_clair(client, db_session):
    from app.modules.auth.models import RefreshToken

    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()

    db_token = db_session.query(RefreshToken).order_by(RefreshToken.id_refresh_token.desc()).first()
    assert db_token.token_hash != tokens["refresh_token"]
    assert auth_services._hasher_token(tokens["refresh_token"]) == db_token.token_hash


def test_logout_revokes_refresh_token(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
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
    _verifier_email(client, db_session)
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

    # Le nouveau mot de passe fonctionne et renvoie directement les jetons
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "nouveaumotdepasse456"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]


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


def test_login_google_pour_un_compte_existant_renvoie_les_jetons(client, monkeypatch):
    client.post("/api/v1/auth/register", json=_register_payload())
    _mocker_id_token_google(monkeypatch)

    response = client.post("/api/v1/auth/google", json={"id_token": "faux-jeton-google"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user_type"] == "client"


def test_login_google_marque_lemail_verifie_meme_sans_otp(client, db_session, monkeypatch):
    """
    Google vient de vérifier cette adresse lui-même (email_verified) : ça
    doit compter aussi pour /auth/login (mot de passe) sur la même
    adresse, jamais bloqué après une connexion Google réussie (voir
    EmailNonVerifieError).
    """
    client.post("/api/v1/auth/register", json=_register_payload())
    _mocker_id_token_google(monkeypatch)
    client.post("/api/v1/auth/google", json={"id_token": "faux-jeton-google"})

    db_utilisateur = db_session.query(Utilisateur).filter(
        Utilisateur.email == "jean.dupont@example.com"
    ).first()
    assert db_utilisateur.email_verifie is True

    reponse = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )
    assert reponse.status_code == 200


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


# --- Tentatives de connexion échouées & notifications ---

def test_connexion_reussie_cree_une_notification_client(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()

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


def test_verrouillage_apres_trop_dechecs_bloque_meme_le_bon_mot_de_passe(client, db_session):
    """
    Voir auth.services.SEUIL_VERROUILLAGE : au-delà d'un nombre soutenu
    d'échecs consécutifs, le compte est verrouillé temporairement — même
    une tentative avec le bon mot de passe est refusée tant que le verrou
    n'a pas expiré (protège contre une force brute distribuée sur
    plusieurs IP, que le rate limit par IP seul ne peut pas voir).
    """
    client.post("/api/v1/auth/register", json=_register_payload())

    for _ in range(auth_services.SEUIL_VERROUILLAGE):
        client.post(
            "/api/v1/auth/login",
            json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
        )

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_client.verrouille_jusqua is not None

    reponse = se_connecter(client, "jean.dupont@example.com", "motdepasse123")
    assert reponse.status_code == 429


def test_le_verrouillage_expire_et_une_connexion_reussie_reinitialise_les_compteurs(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    for _ in range(auth_services.SEUIL_VERROUILLAGE):
        client.post(
            "/api/v1/auth/login",
            json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
        )

    from datetime import datetime, timedelta
    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    db_client.verrouille_jusqua = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()

    reponse = se_connecter(client, "jean.dupont@example.com", "motdepasse123")
    assert reponse.status_code == 200

    db_session.refresh(db_client)
    assert db_client.verrouille_jusqua is None
    assert db_client.tentatives_echouees == 0


# --- Modification des informations d'identité (PUT /auth/me) ---

def test_update_mes_informations_modifie_selectivement_les_champs(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.put(
        "/api/v1/auth/me",
        json={"first_name": "Jeanne", "phone": "+237699999999"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Jeanne"
    assert body["last_name"] == "Dupont"  # non fourni, inchangé
    assert body["phone"] == "+237699999999"


def test_update_mes_informations_requires_authentication(client):
    response = client.put("/api/v1/auth/me", json={"first_name": "Jeanne"})
    assert response.status_code == 401


# --- Changement de mot de passe (PUT /auth/change-password) ---

def test_changer_mot_de_passe_avec_ancien_mot_de_passe_correct(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.put(
        "/api/v1/auth/change-password",
        json={"mot_de_passe_actuel": "motdepasse123", "nouveau_mot_de_passe": "nouveaumotdepasse789"},
        headers=headers,
    )
    assert response.status_code == 200

    ancien_login = client.post(
        "/api/v1/auth/login", json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"}
    )
    assert ancien_login.status_code == 400

    nouveau_login = client.post(
        "/api/v1/auth/login", json={"email": "jean.dupont@example.com", "mot_de_passe": "nouveaumotdepasse789"}
    )
    assert nouveau_login.status_code == 200


def test_changer_mot_de_passe_avec_ancien_mot_de_passe_incorrect_est_rejete(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.put(
        "/api/v1/auth/change-password",
        json={"mot_de_passe_actuel": "mauvais-mot-de-passe", "nouveau_mot_de_passe": "nouveaumotdepasse789"},
        headers=headers,
    )
    assert response.status_code == 400

    inchange_login = client.post(
        "/api/v1/auth/login", json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"}
    )
    assert inchange_login.status_code == 200


def test_changer_mot_de_passe_requires_authentication(client):
    response = client.put(
        "/api/v1/auth/change-password",
        json={"mot_de_passe_actuel": "peuimporte", "nouveau_mot_de_passe": "peuimporte123"},
    )
    assert response.status_code == 401


# --- Photo de profil (POST/DELETE /auth/profile/photo) ---

def _entete_avec_jeton(client) -> dict:
    client.post("/api/v1/auth/register", json=_register_payload())
    tokens = se_connecter(client, "jean.dupont@example.com", "motdepasse123").json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# Signature binaire réelle d'un PNG (voir auth.router._contenu_correspond_au_type_declare)
# — un contenu factice qui ne commence pas par ces octets est désormais
# rejeté même si le Content-Type déclaré est "image/png".
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_uploader_photo_profil_remplace_lavatar(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _entete_avec_jeton(client)

    response = client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("avatar.png", PNG_MAGIC + b"contenu-image-factice", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["avatar"].startswith(f"{settings.BACKEND_URL}/avatars/")
    fichiers = list(tmp_path.iterdir())
    assert len(fichiers) == 1


def test_uploader_photo_profil_rejette_un_format_non_supporte(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _entete_avec_jeton(client)

    response = client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("avatar.gif", b"contenu", "image/gif")},
    )

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_uploader_photo_profil_rejette_un_contenu_qui_ne_correspond_pas_au_type_declare(
    client, db_session, tmp_path, monkeypatch
):
    """
    Le Content-Type est déclaré par le client, jamais garanti — un fichier
    quelconque prétendant être un PNG (mais dont les octets ne correspondent
    pas à la signature réelle) doit être rejeté (voir
    auth.router._contenu_correspond_au_type_declare).
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _entete_avec_jeton(client)

    response = client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("avatar.png", b"<script>alert(1)</script>", "image/png")},
    )

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_uploader_photo_profil_rejette_un_fichier_trop_volumineux(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings
    from app.modules.auth import router as auth_router

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    monkeypatch.setattr(auth_router, "TAILLE_MAX_AVATAR", 10)
    headers = _entete_avec_jeton(client)

    response = client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("avatar.png", b"beaucoup-plus-de-dix-octets", "image/png")},
    )

    assert response.status_code == 400


def test_remplacer_la_photo_supprime_lancien_fichier(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _entete_avec_jeton(client)

    client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("premiere.png", PNG_MAGIC + b"premiere-photo", "image/png")},
    )
    assert len(list(tmp_path.iterdir())) == 1

    client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("seconde.png", PNG_MAGIC + b"seconde-photo", "image/png")},
    )

    # L'ancien fichier a bien été supprimé, un seul fichier reste sur disque.
    assert len(list(tmp_path.iterdir())) == 1


def test_supprimer_photo_profil_efface_le_fichier_et_lavatar(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _entete_avec_jeton(client)

    client.post(
        "/api/v1/auth/profile/photo",
        headers=headers,
        files={"photo": ("avatar.png", PNG_MAGIC + b"contenu-image-factice", "image/png")},
    )
    assert len(list(tmp_path.iterdir())) == 1

    response = client.delete("/api/v1/auth/profile/photo", headers=headers)

    assert response.status_code == 200
    assert response.json()["avatar"] is None
    assert list(tmp_path.iterdir()) == []


def test_une_url_avatar_externe_nest_jamais_supprimee_du_disque(client, db_session, tmp_path, monkeypatch):
    """Un avatar réglé via l'ancien champ texte (PUT /auth/profile, URL
    externe collée manuellement) ne doit jamais déclencher une suppression
    de fichier local — voir services.supprimer_fichier_avatar."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _entete_avec_jeton(client)

    client.put(
        "/api/v1/auth/profile",
        headers=headers,
        json={"avatar": "https://example.com/photo.jpg"},
    )

    response = client.delete("/api/v1/auth/profile/photo", headers=headers)
    assert response.status_code == 200
    assert response.json()["avatar"] is None


def test_avatar_avec_un_schema_non_http_est_rejete(client, db_session):
    """
    L'avatar est affiché publiquement (avis client sur la landing page,
    voir avis.schemas.AvisPublicOut) : accepter n'importe quelle chaîne
    permettrait d'y stocker un schéma javascript:/data: — voir
    auth.schemas.ProfileUpdate._avatar_doit_etre_une_url_http.
    """
    headers = _entete_avec_jeton(client)

    response = client.put(
        "/api/v1/auth/profile",
        headers=headers,
        json={"avatar": "javascript:alert(1)"},
    )

    assert response.status_code == 422


def test_une_connexion_reussie_reinitialise_le_compteur_de_tentatives(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())

    for _ in range(auth_services.SEUIL_ALERTE_TENTATIVES):
        client.post(
            "/api/v1/auth/login",
            json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
        )

    se_connecter(client, "jean.dupont@example.com", "motdepasse123")

    db_client = db_session.query(Utilisateur).filter(Utilisateur.email == "jean.dupont@example.com").first()
    assert db_client.tentatives_echouees == 0
    assert db_client.alerte_tentatives_envoyee is False
