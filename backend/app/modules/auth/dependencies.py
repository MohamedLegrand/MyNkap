from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.models import Utilisateur, Client, Administrateur

# Configure la récupération du token JWT dans l'en-tête Authorization
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(reusable_oauth2)
) -> Utilisateur:
    """
    Extrait le token de l'en-tête, le valide, décode le payload, 
    et renvoie l'utilisateur connecté s'il est actif.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton de connexion invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(Utilisateur).filter(Utilisateur.id_utilisateur == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Utilisateur non trouvé"
        )
    if not user.est_actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Compte utilisateur désactivé"
        )
    return user

def get_current_active_client(
    current_user: Utilisateur = Depends(get_current_user)
) -> Client:
    """
    S'assure que l'utilisateur connecté est un Client.
    """
    if current_user.type != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : cet utilisateur n'est pas un client"
        )
    return current_user

def get_current_active_admin(
    current_user: Utilisateur = Depends(get_current_user)
) -> Administrateur:
    """
    S'assure que l'utilisateur connecté est un Administrateur.
    """
    if current_user.type != "administrateur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé : droits d'administration requis"
        )
    return current_user
