import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.modules.auth.models import Utilisateur, Client, Profile, RefreshToken
from app.modules.auth.schemas import UserRegister, UserLogin, ResetPasswordRequest
from app.modules.budgets import service as budgets_service
from app.modules.notifications import service as notifications_service
from app.modules.plans import service as plans_service

# Nombre de tentatives de connexion échouées consécutives (mot de passe OU
# code OTP) à partir duquel le client est alerté par notification — voir
# _signaler_tentative_echouee.
SEUIL_ALERTE_TENTATIVES = 3


class GoogleTokenInvalideError(Exception):
    """Le jeton d'identité Google fourni est invalide, expiré, ou son audience ne correspond pas à GOOGLE_CLIENT_ID."""


class CompteInexistantPourGoogleError(Exception):
    """Aucun compte MyNkap n'est associé à l'adresse e-mail du compte Google utilisé."""

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
        _signaler_tentative_echouee(db, utilisateur)
        return None
    return utilisateur


# --- Suivi des tentatives de connexion échouées ---

def _signaler_tentative_echouee(db: Session, utilisateur: Utilisateur) -> None:
    """
    Incrémente le compteur d'échecs consécutifs (mot de passe OU code OTP,
    peu importe l'étape) et notifie le client une seule fois par série
    d'échecs dès que SEUIL_ALERTE_TENTATIVES est atteint — jamais
    renotifié à chaque échec supplémentaire tant que le flag reste posé,
    même principe que budgets.service.verifier_alertes. Ne concerne que
    les comptes Client : les notifications admin sont des diffusions
    globales, pas un canal par administrateur individuel (voir
    notifications.service.creer_notification_admins).
    """
    utilisateur.tentatives_echouees += 1
    faut_alerter = (
        utilisateur.tentatives_echouees >= SEUIL_ALERTE_TENTATIVES
        and not utilisateur.alerte_tentatives_envoyee
        and utilisateur.type == "client"
    )
    if faut_alerter:
        utilisateur.alerte_tentatives_envoyee = True
    db.commit()

    if faut_alerter:
        notifications_service.creer_notification_client(
            db, utilisateur.id_utilisateur, "TENTATIVES_ECHOUEES",
            "Tentatives de connexion suspectes",
            f"{utilisateur.tentatives_echouees} tentatives de connexion ont échoué sur votre compte. "
            "Si ce n'est pas vous, changez votre mot de passe par précaution.",
        )


def _reinitialiser_tentatives_echouees(utilisateur: Utilisateur) -> None:
    utilisateur.tentatives_echouees = 0
    utilisateur.alerte_tentatives_envoyee = False

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

    if code_valide:
        _reinitialiser_tentatives_echouees(utilisateur)
        db.commit()
        if utilisateur.type == "client":
            notifications_service.creer_notification_client(
                db, utilisateur.id_utilisateur, "CONNEXION_REUSSIE",
                "Nouvelle connexion à votre compte",
                f"Connexion réussie le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC. "
                "Si ce n'est pas vous, changez votre mot de passe immédiatement.",
            )
        return utilisateur

    db.commit()
    _signaler_tentative_echouee(db, utilisateur)
    return None


# --- Connexion via Google (Google Identity Services) ---

def _verifier_id_token_google(id_token_str: str) -> dict:
    """
    Vérifie la signature, l'émetteur et l'audience (GOOGLE_CLIENT_ID) du
    jeton d'identité renvoyé par le bouton Google côté frontend. Isolée
    dans sa propre fonction pour rester mockable en test — même principe
    que plans.service._appeler_hrpay_cash_in (aucun test ne doit dépendre
    d'un vrai jeton Google, ni faire d'appel réseau réel vers Google).
    """
    return google_id_token.verify_oauth2_token(
        id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
    )


def authentifier_avec_google(db: Session, id_token_str: str) -> Utilisateur:
    """
    Étape 1 (alternative au mot de passe) de la connexion via Google :
    vérifie le jeton d'identité et retrouve le compte MyNkap existant
    associé à son adresse e-mail. Ne crée jamais de compte à la volée —
    Google ne fournit pas de numéro de téléphone, requis à l'inscription
    (Mobile Money) — l'utilisateur doit d'abord s'inscrire normalement.
    Toujours suivie de la même étape OTP que le mot de passe (voir
    generer_et_envoyer_otp) : Google Sign-In ne contourne jamais la double
    authentification.
    """
    try:
        payload = _verifier_id_token_google(id_token_str)
    except ValueError as erreur:
        raise GoogleTokenInvalideError(str(erreur))

    email = payload.get("email")
    if not email or not payload.get("email_verified"):
        raise GoogleTokenInvalideError("L'e-mail du compte Google n'est pas vérifié.")

    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not utilisateur or not utilisateur.est_actif:
        raise CompteInexistantPourGoogleError()

    return utilisateur

# --- Services de gestion des Refresh Tokens ---

def _hasher_token(token: str) -> str:
    """
    Empreinte SHA-256 du jeton en clair — jamais le jeton lui-même n'est
    stocké en base (voir RefreshToken.token_hash). Un hachage rapide
    suffit ici, contrairement aux mots de passe : le jeton a déjà 256 bits
    d'entropie aléatoire (secrets.token_hex), aucun risque de dictionnaire.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def creer_refresh_token(db: Session, client_id: int) -> Tuple[RefreshToken, str]:
    """
    Génère un jeton de rafraîchissement, l'enregistre en base (empreinte
    uniquement) et retourne à la fois l'enregistrement et le jeton en
    clair — ce dernier n'est jamais reconstituable après cet appel, il ne
    doit être transmis qu'une fois au client.
    """
    token_string = secrets.token_hex(32)
    # Le jeton expire dans 8 jours
    expiration = datetime.utcnow() + timedelta(days=8)

    db_refresh = RefreshToken(
        id_client=client_id,
        token_hash=_hasher_token(token_string),
        date_expiration=expiration
    )
    db.add(db_refresh)
    db.commit()
    db.refresh(db_refresh)
    return db_refresh, token_string

def valider_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """
    Vérifie si le jeton existe, n'est pas expiré et n'est pas révoqué.
    """
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == _hasher_token(token),
        RefreshToken.est_revoque == False,
        RefreshToken.date_expiration > datetime.utcnow()
    ).first()
    return db_token

def revoquer_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """
    Révoque un jeton de rafraîchissement en base de données et le retourne
    (ou None si le jeton n'existe pas).
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == _hasher_token(token)).first()
    if db_token:
        db_token.est_revoque = True
        db.commit()
        return db_token
    return None

def faire_tourner_refresh_token(db: Session, ancien: RefreshToken) -> str:
    """
    Révoque l'ancien jeton et en émet un nouveau pour le même utilisateur —
    rotation à chaque rafraîchissement (recommandation OWASP) : toute
    réutilisation ultérieure de l'ancien jeton (déjà révoqué) est donc
    détectable, signe probable d'un vol plutôt qu'un simple double appel
    légitime. Retourne le nouveau jeton en clair.
    """
    ancien.est_revoque = True
    db.commit()
    _, nouveau_token = creer_refresh_token(db, ancien.id_client)
    return nouveau_token

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
