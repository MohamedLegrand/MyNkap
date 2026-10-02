import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx
from fastapi import Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import HACHAGE_FACTICE, get_password_hash, verify_password, create_access_token
from app.modules.audit.service import enregistrer_action
from app.modules.auth.models import Utilisateur, Client, PendingInscription, Profile, RefreshToken
from app.modules.auth.schemas import UserRegister, UserLogin, ResetPasswordRequest
from app.modules.budgets import service as budgets_service
from app.modules.comptes import service as comptes_service
from app.modules.notifications import service as notifications_service
from app.modules.plans import service as plans_service

# Nombre de tentatives de connexion échouées consécutives (mot de passe OU
# code OTP) à partir duquel le client est alerté par notification — voir
# _signaler_tentative_echouee.
SEUIL_ALERTE_TENTATIVES = 3

# Au-delà de ce nombre d'échecs consécutifs, le compte est verrouillé
# temporairement (voir verrouille_jusqua) — le rate limit par IP
# (10/minute sur /auth/login) ne freine pas une attaque par force brute
# répartie sur plusieurs IP visant un seul compte ; ce verrou-là si.
# Volontairement plus élevé que SEUIL_ALERTE_TENTATIVES : la notification
# prévient tôt, le verrou ne bloque qu'en cas d'échecs vraiment soutenus.
SEUIL_VERROUILLAGE = 8
DUREE_VERROUILLAGE = timedelta(minutes=15)

# Un client peut légitimement rejouer le jeton de rafraîchissement qu'il
# vient de faire tourner : la requête a pu réussir côté serveur (rotation
# effectuée) sans que la réponse n'atteigne jamais le client (coupure
# réseau, application tuée en arrière-plan) — sa seule option est alors de
# retenter avec le jeton qu'il a encore. Dans cette fenêtre, une
# réapparition du jeton révoqué est traitée comme une simple retentative
# (401 ordinaire, sans conséquence) plutôt que comme un vol de session — au-
# delà, elle reste un signal fort (voir valider_refresh_token) : un client
# qui a continué à naviguer normalement avec son nouveau jeton n'a aucune
# raison de rejouer l'ancien plusieurs minutes après.
FENETRE_GRACE_REUTILISATION = timedelta(seconds=20)


class GoogleTokenInvalideError(Exception):
    """Le jeton d'identité Google fourni est invalide, expiré, ou son audience ne correspond pas à GOOGLE_CLIENT_ID."""


class CompteInexistantPourGoogleError(Exception):
    """Aucun compte MyNkap n'est associé à l'adresse e-mail du compte Google utilisé."""


class MotDePasseActuelIncorrectError(Exception):
    """Le mot de passe actuel fourni ne correspond pas — changement refusé (voir changer_mot_de_passe)."""


class CompteVerrouilleError(Exception):
    """Trop d'échecs de connexion consécutifs — compte verrouillé temporairement (voir SEUIL_VERROUILLAGE)."""


class EmailNonVerifieError(Exception):
    """
    Identifiants corrects, mais l'adresse e-mail n'a jamais été confirmée
    via le code envoyé à l'inscription (voir verifier_otp) — la connexion
    est refusée tant que ce n'est pas fait. Sans ce contrôle, l'étape OTP
    de l'inscription ne vérifiait rien en pratique : un compte créé avec
    l'e-mail de quelqu'un d'autre (ou une adresse inexistante) restait
    pleinement utilisable sans jamais prouver qu'on en a l'accès.
    """


class RefreshTokenReutiliseError(Exception):
    """
    Un jeton de rafraîchissement déjà révoqué a été présenté à nouveau —
    signe probable de vol de session (voir valider_refresh_token). Toutes
    les sessions actives du client ont déjà été révoquées au moment où
    cette exception est levée ; le routeur ne doit renvoyer qu'un 401
    générique, identique à un jeton simplement invalide.
    """

# --- Services d'Inscription et Connexion ---

def _finaliser_creation_client(
    db: Session, email: str, mot_de_passe_hache: str, first_name: str, last_name: str, phone: str
) -> Client:
    """
    Cœur commun de la création d'un Client (profil par défaut, catégories
    usuelles, essai gratuit, compte Abonnement, notifications) — partagé
    entre creer_client (mot de passe en clair, utilisé par le script de
    seed de démonstration) et confirmer_inscription (mot de passe déjà
    haché, stocké dans PendingInscription depuis demarrer_inscription).
    Prend le mot de passe déjà haché pour ne jamais le hacher deux fois.
    """
    # 1. Création de l'utilisateur de base
    db_client = Client(
        email=email,
        mot_de_passe=mot_de_passe_hache,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        type="client"
    )
    db.add(db_client)
    db.flush()  # Pour récupérer l'id_client généré

    # 2. Création du profil par défaut (XAF / FR)
    db_profile = Profile(
        id_client=db_client.id_client,
        devise="XAF",
        langue="FR"
    )
    db.add(db_profile)

    # 3. Catégories usuelles par défaut, pour que le client puisse
    # enregistrer une transaction dès sa première connexion (voir
    # budgets.service.creer_categories_par_defaut)
    budgets_service.creer_categories_par_defaut(db, db_client.id_client)

    # 4. Essai gratuit de 7 jours, accès complet (voir plans.service.creer_abonnement_essai)
    plans_service.creer_abonnement_essai(db, db_client.id_client)

    # 5. Compte financier dédié au paiement des abonnements — rechargeable
    # par le client et utilisé pour le renouvellement automatique (voir
    # comptes.service.creer_compte_abonnement)
    comptes_service.creer_compte_abonnement(db, db_client.id_client)

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


def creer_client(db: Session, client_in: UserRegister) -> Client:
    """
    Crée un nouvel utilisateur de type Client directement, mot de passe en
    clair — utilisé par le script de seed de démonstration uniquement. Le
    flux public d'inscription (POST /auth/register) ne passe plus par ici :
    voir demarrer_inscription puis confirmer_inscription, qui ne créent le
    Client qu'une fois le code OTP confirmé.
    """
    return _finaliser_creation_client(
        db, client_in.email, get_password_hash(client_in.mot_de_passe),
        client_in.first_name, client_in.last_name, client_in.phone,
    )

def authentifier_utilisateur(db: Session, login_in: UserLogin) -> Optional[Utilisateur]:
    """
    Valide les identifiants de l'utilisateur, ouvre directement la session
    (plus de double authentification par OTP à chaque connexion, une seule
    fois à l'inscription — voir verifier_otp) et retourne son modèle s'il
    est valide.

    Lève EmailNonVerifieError si le mot de passe est correct mais que
    l'e-mail n'a jamais été confirmé : c'est ce contrôle, et lui seul, qui
    rend la vérification par OTP réellement obligatoire — un compte créé
    avec un e-mail non maîtrisé ne doit jamais devenir utilisable.
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == login_in.email).first()
    if not utilisateur or not utilisateur.est_actif:
        # Fait quand même tourner bcrypt sur un hachage factice : sans ça,
        # cette branche répond bien plus vite qu'un compte existant (qui,
        # lui, attend verify_password ci-dessous) — un écart de latence
        # mesurable à distance qui permettrait de deviner quels e-mails sont
        # inscrits sans jamais tenter un seul mot de passe.
        verify_password(login_in.mot_de_passe, HACHAGE_FACTICE)
        return None
    if utilisateur.verrouille_jusqua is not None and utilisateur.verrouille_jusqua > datetime.utcnow():
        raise CompteVerrouilleError()
    if not verify_password(login_in.mot_de_passe, utilisateur.mot_de_passe):
        _signaler_tentative_echouee(db, utilisateur)
        return None
    if not utilisateur.email_verifie:
        raise EmailNonVerifieError()

    _reinitialiser_tentatives_echouees(utilisateur)
    db.commit()
    _notifier_connexion_reussie(db, utilisateur)
    return utilisateur


def changer_mot_de_passe(
    db: Session, utilisateur: Utilisateur, mot_de_passe_actuel: str, nouveau_mot_de_passe: str
) -> None:
    """
    Changement de mot de passe pour un client déjà connecté (voir
    PUT /auth/change-password) — distinct du flux mot de passe oublié
    (reinitialiser_mot_de_passe) : ici on exige de prouver la connaissance
    du mot de passe actuel plutôt qu'un jeton reçu par e-mail.
    """
    if not verify_password(mot_de_passe_actuel, utilisateur.mot_de_passe):
        raise MotDePasseActuelIncorrectError()
    utilisateur.mot_de_passe = get_password_hash(nouveau_mot_de_passe)
    db.commit()


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
    if utilisateur.tentatives_echouees >= SEUIL_VERROUILLAGE:
        utilisateur.verrouille_jusqua = datetime.utcnow() + DUREE_VERROUILLAGE
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
    utilisateur.verrouille_jusqua = None


def _notifier_connexion_reussie(db: Session, utilisateur: Utilisateur) -> None:
    """Notifie le client (jamais les administrateurs, canal individuel
    uniquement) d'une connexion réussie — appelée après authentifier_utilisateur
    ET authentifier_avec_google, les deux seules façons d'ouvrir une session."""
    if utilisateur.type == "client":
        notifications_service.creer_notification_client(
            db, utilisateur.id_utilisateur, "CONNEXION_REUSSIE",
            "Nouvelle connexion à votre compte",
            f"Connexion réussie le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC. "
            "Si ce n'est pas vous, changez votre mot de passe immédiatement.",
        )

# --- Émission de la session (jetons) ---

def emettre_session(db: Session, utilisateur: Utilisateur) -> dict:
    """
    Émet les jetons de session (access + refresh) pour un utilisateur déjà
    authentifié — factorisé entre /auth/login et /auth/google, les deux
    seules routes qui ouvrent une session directement.
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=utilisateur.id_utilisateur, expires_delta=access_token_expires
    )
    _, refresh_token_str = creer_refresh_token(db, utilisateur.id_utilisateur)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_type": utilisateur.type,
    }

# --- Inscription en attente de confirmation par code OTP ---
#
# Le Client n'est créé qu'une fois le code confirmé (voir
# confirmer_inscription) — jamais à POST /auth/register. Les fonctions
# generer_et_envoyer_otp/verifier_otp ci-dessous restent le chemin LEGACY :
# elles ne concernent que les comptes Client créés avant ce changement et
# encore non vérifiés (voir PendingInscription pour le détail), un cas qui
# ne peut plus se produire pour une inscription démarrée après.

DUREE_VALIDITE_OTP_INSCRIPTION = timedelta(minutes=45)


def _construire_email_otp(code: str) -> str:
    return (
        f"<p>Bonjour,</p>"
        f"<p>Voici votre code de vérification MyNkap, valable 45 minutes :</p>"
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:6px;color:#254E2A;">{code}</p>'
        f"<p>Si vous n'êtes pas à l'origine de cette inscription, ignorez cet e-mail.</p>"
    )


def demarrer_inscription(db: Session, client_in: UserRegister) -> PendingInscription:
    """
    Démarre (ou renouvelle si un essai précédent pour cet e-mail n'a jamais
    été confirmé — c'est ce que rappelle le bouton "renvoyer le code" du
    frontend, OtpVerificationStep.onResend, qui rappelle POST /auth/register
    à l'identique) une inscription en attente et lui envoie un code OTP.
    N'est appelée que si aucun Utilisateur (vérifié ou legacy non vérifié)
    n'existe déjà pour cet e-mail — voir router.register.
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    expiration = datetime.utcnow() + DUREE_VALIDITE_OTP_INSCRIPTION

    pending = db.query(PendingInscription).filter(PendingInscription.email == client_in.email).first()
    if pending is None:
        pending = PendingInscription(email=client_in.email)
        db.add(pending)

    pending.mot_de_passe = get_password_hash(client_in.mot_de_passe)
    pending.first_name = client_in.first_name
    pending.last_name = client_in.last_name
    pending.phone = client_in.phone
    pending.otp_code = code
    pending.otp_expiration = expiration
    db.commit()

    _envoyer_email_brevo(pending.email, "Votre code de vérification MyNkap", _construire_email_otp(code))
    return pending


def confirmer_inscription(db: Session, email: str, code: str, request: Optional[Request] = None) -> Optional[Client]:
    """
    Valide le code d'une inscription en attente (voir demarrer_inscription)
    et, seulement si le code est correct et non expiré, crée réellement le
    Client (profil, catégories par défaut, essai gratuit, compte Abonnement
    — voir _finaliser_creation_client), tracé dans l'AuditLog ("CREER",
    comme l'ancien flux le faisait à l'inscription — voir router.register).
    Invalide le code dans tous les cas (usage unique). Renvoie None si
    aucune inscription en attente n'existe pour cet e-mail (y compris le
    cas où elle a déjà été confirmée, ou n'a jamais existé — voir
    router.verify_otp pour le repli vers l'ancien mécanisme, verifier_otp).
    """
    pending = db.query(PendingInscription).filter(PendingInscription.email == email).first()
    if pending is None:
        return None
    if not pending.otp_code or not pending.otp_expiration:
        return None

    code_valide = (
        pending.otp_expiration >= datetime.utcnow()
        and secrets.compare_digest(pending.otp_code, code)
    )

    pending.otp_code = None
    pending.otp_expiration = None

    if not code_valide:
        db.commit()
        return None

    db.commit()  # persiste l'invalidation du code avant de créer le compte

    client = _finaliser_creation_client(
        db, pending.email, pending.mot_de_passe, pending.first_name, pending.last_name, pending.phone,
    )
    client.email_verifie = True
    db.commit()

    db.delete(pending)
    db.commit()

    enregistrer_action(
        db,
        id_utilisateur=client.id_client,
        action="CREER",
        ressource="Client",
        id_ressource=client.id_client,
        donnees_apres={"email": client.email},
        request=request,
    )

    return client


def generer_et_envoyer_otp(db: Session, utilisateur: Utilisateur) -> None:
    """
    LEGACY — ne concerne que les comptes Client créés avant l'introduction
    de PendingInscription, encore non vérifiés (voir router.register).
    Génère un code à 6 chiffres valable 45 minutes et l'envoie par e-mail
    (Brevo). Durée alignée sur le délai de renvoi côté frontend
    (OtpVerificationStep.DUREE_COOLDOWN_RENVOI_SECONDES) : le code reste
    valide pendant toute la fenêtre où le bouton "renvoyer" est désactivé,
    sinon un client lent à consulter ses e-mails se retrouverait bloqué
    sans code utilisable ni possibilité d'en redemander un.
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    utilisateur.otp_code = code
    utilisateur.otp_expiration = datetime.utcnow() + DUREE_VALIDITE_OTP_INSCRIPTION
    db.commit()

    _envoyer_email_brevo(utilisateur.email, "Votre code de vérification MyNkap", _construire_email_otp(code))


def verifier_otp(db: Session, email: str, code: str) -> Optional[Utilisateur]:
    """
    LEGACY — voir generer_et_envoyer_otp. Valide le code OTP envoyé à
    l'inscription pour l'e-mail donné et marque l'adresse comme vérifiée.
    Retourne l'utilisateur si le code est correct, non expiré, et le
    compte toujours actif — invalide le code dans tous les cas (usage
    unique). N'ouvre aucune session : voir authentifier_utilisateur
    (POST /auth/login) pour se connecter ensuite.
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
        utilisateur.email_verifie = True
        db.commit()
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
    Connexion via Google (alternative au mot de passe) : vérifie le jeton
    d'identité, retrouve le compte MyNkap existant associé à son adresse
    e-mail et ouvre directement la session, comme authentifier_utilisateur
    — Google étant déjà un fournisseur d'identité vérifié (email_verified),
    aucune étape OTP supplémentaire n'est nécessaire.

    Ne crée jamais de compte à partir de rien — Google ne fournit pas de
    numéro de téléphone, requis à l'inscription (Mobile Money). En
    revanche, si une inscription en attente existe pour cette adresse
    (voir PendingInscription : l'utilisateur s'est déjà inscrit par
    e-mail/mot de passe, téléphone inclus, mais n'a pas encore saisi le
    code reçu par Brevo), Google vient de prouver que l'adresse est bien
    joignable — exactement ce que le code OTP établirait — donc ça
    finalise la création du compte avec les informations déjà fournies à
    l'inscription, sans attendre l'e-mail Brevo.
    """
    try:
        payload = _verifier_id_token_google(id_token_str)
    except ValueError as erreur:
        raise GoogleTokenInvalideError(str(erreur))

    email = payload.get("email")
    if not email or not payload.get("email_verified"):
        raise GoogleTokenInvalideError("L'e-mail du compte Google n'est pas vérifié.")
    email = email.strip().lower()

    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if utilisateur is not None and not utilisateur.est_actif:
        raise CompteInexistantPourGoogleError()

    if utilisateur is None:
        pending = db.query(PendingInscription).filter(PendingInscription.email == email).first()
        if pending is None:
            raise CompteInexistantPourGoogleError()
        utilisateur = _finaliser_creation_client(
            db, pending.email, pending.mot_de_passe, pending.first_name, pending.last_name, pending.phone,
        )
        db.delete(pending)
        db.commit()

    # Google vient de vérifier cette adresse (email_verified ci-dessus) :
    # marque l'e-mail confirmé s'il ne l'était pas encore, pour que la
    # connexion par mot de passe (voir authentifier_utilisateur,
    # EmailNonVerifieError) ne reste pas bloquée après une connexion Google
    # réussie sur la même adresse.
    utilisateur.email_verifie = True
    _reinitialiser_tentatives_echouees(utilisateur)
    db.commit()
    _notifier_connexion_reussie(db, utilisateur)
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

    Un jeton de rafraîchissement n'est présenté qu'une seule fois dans un
    usage normal : chaque appel à /auth/refresh le révoque et en émet un
    nouveau (rotation, voir faire_tourner_refresh_token). Sa réapparition
    après révocation n'est donc quasiment jamais un simple double appel
    légitime — sauf dans la toute petite fenêtre suivant la rotation, où
    elle peut aussi être une retentative réseau bénigne (voir
    FENETRE_GRACE_REUTILISATION). Passé cette fenêtre, c'est un signal fort
    de vol : le client légitime a eu largement le temps de recevoir et
    utiliser son nouveau jeton, donc rejouer l'ancien n'a plus de
    justification bénigne. Dans ce cas (hash connu, déjà révoqué, hors
    fenêtre de grâce), on révoque par précaution toutes les sessions
    actives du client et on lève RefreshTokenReutiliseError plutôt que de
    se contenter de refuser ce seul jeton — la réponse HTTP reste un 401
    générique dans tous les cas (voir router.refresh_token), pour ne rien
    révéler à qui rejoue le jeton.
    """
    token_hash = _hasher_token(token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if db_token is not None and db_token.est_revoque:
        dans_la_fenetre_de_grace = (
            db_token.date_revocation is not None
            and datetime.utcnow() - db_token.date_revocation <= FENETRE_GRACE_REUTILISATION
        )
        if dans_la_fenetre_de_grace:
            return None

        nb_revoques = db.query(RefreshToken).filter(
            RefreshToken.id_client == db_token.id_client,
            RefreshToken.est_revoque == False,
        ).update({"est_revoque": True, "date_revocation": datetime.utcnow()})
        db.commit()
        if nb_revoques:
            notifications_service.creer_notification_client(
                db, db_token.id_client, "SECURITE_SESSION_COMPROMISE",
                "Toutes vos sessions ont été déconnectées",
                "Un jeton de connexion déjà utilisé a été présenté à nouveau, ce qui peut indiquer "
                "un vol de session. Par précaution, tous vos appareils ont été déconnectés. "
                "Changez votre mot de passe si cette activité ne vous semble pas familière.",
            )
        raise RefreshTokenReutiliseError()

    if db_token is None or db_token.date_expiration <= datetime.utcnow():
        return None
    return db_token

def revoquer_refresh_token(db: Session, token: str) -> Optional[RefreshToken]:
    """
    Révoque un jeton de rafraîchissement en base de données et le retourne
    (ou None si le jeton n'existe pas).
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == _hasher_token(token)).first()
    if db_token:
        db_token.est_revoque = True
        db_token.date_revocation = datetime.utcnow()
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
    ancien.date_revocation = datetime.utcnow()
    db.commit()
    _, nouveau_token = creer_refresh_token(db, ancien.id_client)
    return nouveau_token

# --- Photo de profil (voir router.py, POST/DELETE /auth/profile/photo) ---

def supprimer_fichier_avatar(avatar_url: Optional[str]) -> None:
    """
    Supprime le fichier local d'une ancienne photo de profil, si elle a bien
    été hébergée par MyNkap (jamais une URL externe collée manuellement —
    voir ProfileUpdate.avatar, resté possible pour compatibilité) — évite
    d'accumuler des fichiers orphelins à chaque remplacement/suppression de
    photo.
    """
    prefixe = f"{settings.BACKEND_URL}/avatars/"
    if not avatar_url or not avatar_url.startswith(prefixe):
        return
    nom_fichier = avatar_url[len(prefixe):]
    chemin = os.path.join(settings.AVATARS_DOSSIER, nom_fichier)
    if os.path.isfile(chemin):
        try:
            os.remove(chemin)
        except OSError:
            pass


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
