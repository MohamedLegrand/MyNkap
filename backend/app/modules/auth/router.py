from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    ProfileOut,
    ProfileUpdate,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.modules.auth import services
from app.modules.audit.service import enregistrer_action

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, client_in: UserRegister, db: Session = Depends(get_db)):
    """
    Inscription d'un nouveau client et initialisation de son profil financier.
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

    return nouveau_client

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Connexion d'un utilisateur (Client ou Administrateur) et génération des jetons.
    """
    utilisateur = services.authentifier_utilisateur(db, login_in)
    if not utilisateur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adresse e-mail ou mot de passe incorrect."
        )

    # Durée de validité du jeton d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=utilisateur.id_utilisateur, expires_delta=access_token_expires
    )
    
    # Génération du Refresh Token en BDD
    refresh_token_db = services.creer_refresh_token(db, utilisateur.id_utilisateur)

    enregistrer_action(
        db,
        id_utilisateur=utilisateur.id_utilisateur,
        action="CONNEXION",
        ressource="Utilisateur",
        id_ressource=utilisateur.id_utilisateur,
        request=request,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_db.token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_in: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Renouveler un jeton d'accès (Access Token) expiré en utilisant un jeton de rafraîchissement (Refresh Token).
    """
    db_token = services.valider_refresh_token(db, refresh_in.refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton de rafraîchissement invalide, expiré ou révoqué."
        )

    # Nouveau token d'accès
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        subject=db_token.id_client, expires_delta=access_token_expires
    )

    return {
        "access_token": new_access_token,
        "refresh_token": db_token.token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
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
