import secrets
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.modules.auth.models import Utilisateur, Client, Profile, RefreshToken
from app.modules.auth.schemas import UserRegister, UserLogin, ResetPasswordRequest
from app.modules.budgets import service as budgets_service
from app.modules.notifications import service as notifications_service
from app.modules.plans import service as plans_service

# --- Services d'Inscription et Connexion ---

def creer_client(db: Session, client_in: UserRegister) -> Client:
    """
    Crée un nouvel utilisateur de type Client, lui génère son profil par défaut,
    et persiste le tout en base de données.
    """
    # 1. Hachage du mot de passe
    mot_de_passe_hache = get_password_hash(client_in.mot_de_passe)

    # 2. Création de l'utilisateur de base
    db_client = Client(
        email=client_in.email,
        mot_de_passe=mot_de_passe_hache,
        first_name=client_in.first_name,
        last_name=client_in.last_name,
        phone=client_in.phone,
        type="client"
    )
    db.add(db_client)
    db.flush()  # Pour récupérer l'id_client généré

    # 3. Création du profil par défaut (XAF / FR)
    db_profile = Profile(
        id_client=db_client.id_client,
        devise="XAF",
        langue="FR"
    )
    db.add(db_profile)

    # 4. Catégories usuelles par défaut, pour que le client puisse
    # enregistrer une transaction dès sa première connexion (voir
    # budgets.service.creer_categories_par_defaut)
    budgets_service.creer_categories_par_defaut(db, db_client.id_client)

    # 5. Abonnement GRATUIT par défaut (voir plans.service.creer_abonnement_gratuit)
    plans_service.creer_abonnement_gratuit(db, db_client.id_client)

    db.commit()
    db.refresh(db_client)

    # 6. Notifications (bienvenue côté client, signalement côté admin) —
    # non bloquantes pour l'inscription : gérées dans leur propre commit,
    # après que le client existe déjà réellement en base.
    notifications_service.creer_notification_client(
        db, db_client.id_client, "BIENVENUE",
        "Bienvenue sur MyNkap !",
        f"Bonjour {db_client.first_name}, votre compte a été créé avec succès. "
        "Découvrez vos comptes, vos budgets et votre assistant financier.",
    )
    notifications_service.creer_notification_admins(
        db, "NOUVEAU_CLIENT",
        "Nouveau client inscrit",
        f"{db_client.first_name} {db_client.last_name} ({db_client.email}) vient de créer un compte.",
        lien="/admin?tab=clients",
    )

    return db_client

def authentifier_utilisateur(db: Session, login_in: UserLogin) -> Optional[Utilisateur]:
    """
    Valide les identifiants de l'utilisateur et retourne son modèle s'il est valide.
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == login_in.email).first()
    if not utilisateur or not utilisateur.est_actif:
        return None
    if not verify_password(login_in.mot_de_passe, utilisateur.mot_de_passe):
        return None
    return utilisateur

# --- Services de double authentification par code OTP (e-mail) ---

def generer_et_envoyer_otp(db: Session, utilisateur: Utilisateur) -> None:
    """
    Génère un code à 6 chiffres valable 5 minutes et l'envoie par e-mail
    (Brevo). Appelé après validation du mot de passe, avant l'émission des
    jetons de session — voir verifier_otp() pour la seconde étape.
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    utilisateur.otp_code = code
    utilisateur.otp_expiration = datetime.utcnow() + timedelta(minutes=5)
    db.commit()

    contenu_html = (
        f"<p>Bonjour,</p>"
        f"<p>Voici votre code de vérification MyNkap, valable 5 minutes :</p>"
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:6px;color:#254E2A;">{code}</p>'
        f"<p>Si vous n'êtes pas à l'origine de cette connexion, ignorez cet e-mail et changez votre mot de passe.</p>"
    )
    _envoyer_email_brevo(utilisateur.email, "Votre code de vérification MyNkap", contenu_html)


def verifier_otp(db: Session, email: str, code: str) -> Optional[Utilisateur]:
    """
    Valide le code OTP soumis pour l'e-mail donné. Retourne l'utilisateur si
    le code est correct, non expiré, et le compte toujours actif — invalide
    le code dans tous les cas (usage unique).
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not utilisateur or not utilisateur.est_actif:
        return None
    if not utilisateur.otp_code or not utilisateur.otp_expiration:
        return None

    code_valide = (
        utilisateur.otp_expiration >= datetime.utcnow()
        and secrets.compare_digest(utilisateur.otp_code, code)
    )

    utilisateur.otp_code = None
    utilisateur.otp_expiration = None
    db.commit()

    return utilisateur if code_valide else None

# --- Services de gestion des Refresh Tokens ---

def creer_refresh_token(db: Session, client_id: int) -> RefreshToken:
    """
    Génère un jeton de rafraîchissement unique, l'enregistre en base et le retourne.
    """
    token_string = secrets.token_hex(32)
    # Le jeton expire dans 8 jours
    expiration = datetime.utcnow() + timedelta(days=8)
    
    db_refresh = RefreshToken(
        id_client=client_id,
        token=token_string,
        date_expiration=expiration
    )
    db.add(db_refresh)
    db.commit()
    db.refresh(db_refresh)
    return db_refresh

def valider_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """
    Vérifie si le jeton existe, n'est pas expiré et n'est pas révoqué.
    """
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.est_revoque == False,
        RefreshToken.date_expiration > datetime.utcnow()
    ).first()
    return db_token

def revoquer_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """
    Révoque un jeton de rafraîchissement en base de données et le retourne
    (ou None si le jeton n'existe pas).
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db_token.est_revoque = True
        db.commit()
        return db_token
    return None

# --- Services de récupération de mot de passe ---

def _envoyer_email_brevo(destinataire: str, sujet: str, contenu_html: str) -> None:
    """
    Envoie un e-mail transactionnel via l'API REST Brevo. Sans clé configurée
    (clone du dépôt, tests), se contente d'un affichage console — jamais
    d'appel réseau non désiré. Fonction privée séparée pour rester
    monkeypatchable dans les tests, comme _appeler_hrpay_cash_in dans
    plans.service.
    """
    if not settings.BREVO_API_KEY:
        print(f"\n[E-MAIL SIMULATION] Destinataire : {destinataire}")
        print(f"[E-MAIL SIMULATION] Sujet : {sujet}")
        print(f"[E-MAIL SIMULATION] Contenu : {contenu_html}\n")
        return

    try:
        reponse = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
                "accept": "application/json",
            },
            json={
                "sender": {"name": settings.MAIL_FROM_NAME, "email": settings.MAIL_FROM_EMAIL},
                "to": [{"email": destinataire}],
                "subject": sujet,
                "htmlContent": contenu_html,
            },
            timeout=10.0,
        )
        reponse.raise_for_status()
    except httpx.HTTPError as exc:
        # Ne jamais faire échouer le flux de mot de passe oublié à cause d'un
        # incident du fournisseur d'e-mail : le jeton reste valide en base et
        # la réponse de l'API reste générique dans tous les cas (pas de fuite
        # d'information sur l'existence du compte).
        print(f"[BREVO] Échec de l'envoi à {destinataire} : {exc}")


def generer_forgot_password_token(db: Session, email: str) -> Optional[str]:
    """
    Génère un jeton de récupération pour le compte client associé à l'email donné.
    """
    client = db.query(Client).filter(Client.email == email).first()
    if not client:
        return None

    # Génération d'un token aléatoire sécurisé
    reset_token = secrets.token_urlsafe(32)
    client.reset_password_token = reset_token
    # Le token expire dans 15 minutes
    client.reset_password_expires = datetime.utcnow() + timedelta(minutes=15)

    db.commit()

    lien_reinitialisation = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    contenu_html = (
        f"<p>Bonjour {client.first_name},</p>"
        f"<p>Vous avez demandé la réinitialisation de votre mot de passe MyNkap. "
        f"Ce lien est valable 15 minutes :</p>"
        f'<p><a href="{lien_reinitialisation}" '
        f'style="background-color:#254E2A;color:#ffffff;padding:10px 20px;'
        f'border-radius:6px;text-decoration:none;">Réinitialiser mon mot de passe</a></p>'
        f"<p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail.</p>"
    )
    _envoyer_email_brevo(client.email, "Réinitialisation de votre mot de passe MyNkap", contenu_html)

    return reset_token

def reinitialiser_mot_de_passe(db: Session, reset_in: ResetPasswordRequest) -> Optional[Client]:
    """
    Valide le jeton de récupération, applique le nouveau mot de passe et
    retourne le client concerné (ou None si le jeton est invalide/expiré).
    """
    client = db.query(Client).filter(
        Client.reset_password_token == reset_in.token,
        Client.reset_password_expires > datetime.utcnow()
    ).first()

    if not client:
        return None

    # Mise à jour du mot de passe
    client.mot_de_passe = get_password_hash(reset_in.nouveau_mot_de_passe)
    # Nettoyage du token
    client.reset_password_token = None
    client.reset_password_expires = None

    db.commit()
    return client
