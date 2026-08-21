import os
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Utilisateur
from app.modules.auth.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefreshRequest,
    ClientOut,
    ClientInfoUpdate,
    ChangePasswordRequest,
    ProfileOut,
    ProfileUpdate,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RegisterOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
    GoogleLoginRequest,
)
from app.modules.auth import services
from app.modules.audit.service import enregistrer_action

# Formats acceptés pour une photo de profil, et l'extension de fichier
# correspondante — jamais l'extension d'origine du fichier envoyé, qui n'a
# aucune garantie de correspondre à son contenu réel.
EXTENSIONS_PAR_TYPE_AVATAR = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
TAILLE_MAX_AVATAR = 3 * 1024 * 1024  # 3 Mo

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=RegisterOtpResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, client_in: UserRegister, db: Session = Depends(get_db)):
    """
    Inscription d'un nouveau client et initialisation de son profil financier.
    Le compte est créé immédiatement, mais aucun jeton n'est émis ici : un
    code de vérification à 6 chiffres part par e-mail (même mécanisme que
    la double authentification à la connexion, voir services.generer_et_envoyer_otp)
    pour confirmer que l'adresse fournie est bien joignable avant tout accès
    réel — voir POST /auth/verify-otp pour la seconde étape.
    """
    # Vérifier si l'email existe déjà
    utilisateur_existant = db.query(Utilisateur).filter(Utilisateur.email == client_in.email).first()
    if utilisateur_existant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse e-mail est déjà enregistrée."
        )

    # Créer le client
    nouveau_client = services.creer_client(db, client_in)

    enregistrer_action(
        db,
        id_utilisateur=nouveau_client.id_client,
        action="CREER",
        ressource="Client",
        id_ressource=nouveau_client.id_client,
        donnees_apres={"email": nouveau_client.email},
        request=request,
    )

    services.generer_et_envoyer_otp(db, nouveau_client)

    return {
        "otp_requis": True,
        "message": "Compte créé. Un code de vérification a été envoyé par e-mail.",
        "expires_in": 300,
    }

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Connexion par e-mail et mot de passe : émet directement les jetons de
    session. La double authentification par OTP ne s'applique plus qu'à
    l'inscription, pour vérifier l'adresse e-mail une seule fois (voir
    POST /auth/register puis POST /auth/verify-otp), pas à chaque connexion.
    """
    utilisateur = services.authentifier_utilisateur(db, login_in)
    if not utilisateur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adresse e-mail ou mot de passe incorrect."
        )

    session = services.emettre_session(db, utilisateur)

    enregistrer_action(
        db,
        id_utilisateur=utilisateur.id_utilisateur,
        action="CONNEXION",
        ressource="Utilisateur",
        id_ressource=utilisateur.id_utilisateur,
        request=request,
    )

    return session

@router.post("/google", response_model=TokenResponse)
@limiter.limit("10/minute")
def login_google(request: Request, payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Connexion via Google (alternative au mot de passe) : vérifie le jeton
    d'identité Google et émet directement les jetons de session, comme
    /auth/login. Ne fonctionne que pour un compte MyNkap déjà existant
    (voir services.authentifier_avec_google) : Google ne fournit pas de
    numéro de téléphone, requis à l'inscription.
    """
    try:
        utilisateur = services.authentifier_avec_google(db, payload.id_token)
    except services.GoogleTokenInvalideError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeton d'identité Google invalide ou expiré.",
        )
    except services.CompteInexistantPourGoogleError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun compte MyNkap n'est associé à cette adresse Google. Créez d'abord un compte.",
        )

    session = services.emettre_session(db, utilisateur)

    enregistrer_action(
        db,
        id_utilisateur=utilisateur.id_utilisateur,
        action="CONNEXION",
        ressource="Utilisateur",
        id_ressource=utilisateur.id_utilisateur,
        request=request,
    )

    return session

@router.post("/verify-otp", response_model=VerifyOtpResponse)
@limiter.limit("10/minute")
def verify_otp(request: Request, payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Confirme le code de vérification envoyé à l'inscription (voir POST
    /auth/register) et marque l'adresse e-mail comme vérifiée. N'émet
    aucun jeton de session : le client doit ensuite se connecter
    normalement via POST /auth/login.
    """
    utilisateur = services.verifier_otp(db, payload.email, payload.code)
    if not utilisateur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de vérification invalide ou expiré."
        )

    return {"message": "Adresse e-mail vérifiée avec succès. Vous pouvez maintenant vous connecter."}

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh_token(request: Request, refresh_in: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Renouveler un jeton d'accès (Access Token) expiré en utilisant un jeton
    de rafraîchissement (Refresh Token). Fait tourner ce dernier à chaque
    appel (voir services.faire_tourner_refresh_token) : le jeton renvoyé
    ici remplace celui fourni, qui devient invalide immédiatement.
    """
    db_token = services.valider_refresh_token(db, refresh_in.refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton de rafraîchissement invalide, expiré ou révoqué."
        )

    utilisateur = db.query(Utilisateur).filter(Utilisateur.id_utilisateur == db_token.id_client).first()

    # Nouveau token d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        subject=db_token.id_client, expires_delta=access_token_expires
    )
    nouveau_refresh_token = services.faire_tourner_refresh_token(db, db_token)

    return {
        "access_token": new_access_token,
        "refresh_token": nouveau_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_type": utilisateur.type,
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, refresh_in: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Déconnexion en révoquant le jeton de rafraîchissement.
    """
    db_token = services.revoquer_refresh_token(db, refresh_in.refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de révoquer le jeton fourni."
        )

    enregistrer_action(
        db,
        id_utilisateur=db_token.id_client,
        action="DECONNEXION",
        ressource="Utilisateur",
        id_ressource=db_token.id_client,
        request=request,
    )

    return {"message": "Déconnexion réussie."}

@router.get("/me", response_model=ClientOut)
def read_users_me(current_client: Utilisateur = Depends(get_current_active_client)):
    """
    Récupérer les informations de l'utilisateur connecté.
    """
    return current_client

@router.put("/profile", response_model=ProfileOut)
def update_profile(
    profile_update: ProfileUpdate,
    current_client: Utilisateur = Depends(get_current_active_client),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour les préférences de profil du client connecté (langue, devise, avatar).
    """
    profile = current_client.profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil non trouvé."
        )

    # Mise à jour sélective
    if profile_update.avatar is not None:
        profile.avatar = profile_update.avatar
    if profile_update.devise is not None:
        profile.devise = profile_update.devise
    if profile_update.langue is not None:
        profile.langue = profile_update.langue

    db.commit()
    db.refresh(profile)
    return profile

@router.put("/me", response_model=ClientOut)
def update_mes_informations(
    payload: ClientInfoUpdate,
    current_client: Utilisateur = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Modifier son identité (prénom, nom, téléphone) — mise à jour sélective,
    l'e-mail n'est volontairement pas modifiable ici (voir ClientInfoUpdate)."""
    if payload.first_name is not None:
        current_client.first_name = payload.first_name
    if payload.last_name is not None:
        current_client.last_name = payload.last_name
    if payload.phone is not None:
        current_client.phone = payload.phone

    db.commit()
    db.refresh(current_client)
    return current_client

@router.post("/profile/photo", response_model=ProfileOut)
async def uploader_photo_profil(
    photo: UploadFile = File(...),
    current_client: Utilisateur = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """
    Remplace la photo de profil du client connecté. L'ancien fichier (s'il
    en existe un hébergé par MyNkap) est supprimé du disque après succès —
    voir services.supprimer_fichier_avatar.
    """
    profile = current_client.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil non trouvé.")

    extension = EXTENSIONS_PAR_TYPE_AVATAR.get(photo.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non supporté (JPEG, PNG ou WebP uniquement).",
        )

    contenu = await photo.read()
    if len(contenu) > TAILLE_MAX_AVATAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La photo dépasse la taille maximale autorisée (3 Mo).",
        )

    ancien_avatar = profile.avatar
    os.makedirs(settings.AVATARS_DOSSIER, exist_ok=True)
    nom_fichier = f"client_{current_client.id_client}_{uuid.uuid4().hex}{extension}"
    with open(os.path.join(settings.AVATARS_DOSSIER, nom_fichier), "wb") as fichier:
        fichier.write(contenu)

    profile.avatar = f"{settings.BACKEND_URL}/avatars/{nom_fichier}"
    db.commit()
    db.refresh(profile)

    services.supprimer_fichier_avatar(ancien_avatar)
    return profile

@router.delete("/profile/photo", response_model=ProfileOut)
def supprimer_photo_profil(
    current_client: Utilisateur = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Retire la photo de profil du client connecté (retour à l'avatar par défaut)."""
    profile = current_client.profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil non trouvé.")

    ancien_avatar = profile.avatar
    profile.avatar = None
    db.commit()
    db.refresh(profile)

    services.supprimer_fichier_avatar(ancien_avatar)
    return profile

@router.put("/change-password", status_code=status.HTTP_200_OK)
def changer_mon_mot_de_passe(
    payload: ChangePasswordRequest,
    current_client: Utilisateur = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Change le mot de passe du client connecté (nécessite l'ancien mot de
    passe) — distinct de POST /auth/reset-password, réservé au client qui a
    perdu l'accès à son compte."""
    try:
        services.changer_mot_de_passe(
            db, current_client, payload.mot_de_passe_actuel, payload.nouveau_mot_de_passe
        )
    except services.MotDePasseActuelIncorrectError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect.",
        )
    return {"message": "Mot de passe modifié avec succès."}

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def forgot_password(request: Request, forgot_in: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Demander un lien de récupération de mot de passe.
    """
    services.generer_forgot_password_token(db, forgot_in.email)
    # Message générique pour éviter le dénombrement d'utilisateurs
    return {
        "message": "Si l'adresse email existe, un message de récupération a été simulé dans la console."
    }

@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
def reset_password(request: Request, reset_in: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Valider le jeton et définir le nouveau mot de passe.
    """
    client = services.reinitialiser_mot_de_passe(db, reset_in)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jeton de réinitialisation invalide ou expiré."
        )

    enregistrer_action(
        db,
        id_utilisateur=client.id_client,
        action="RESET_PASSWORD",
        ressource="Client",
        id_ressource=client.id_client,
        request=request,
    )

    return {"message": "Mot de passe modifié avec succès."}
