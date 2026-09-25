from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hachage bcrypt valide mais sans mot de passe en clair connu de personne —
# sert uniquement à faire consommer à verify_password() le même coût CPU
# qu'une vérification réelle quand l'utilisateur n'existe pas (voir
# auth.services.authentifier_utilisateur). Sans ça, un e-mail inexistant
# répond immédiatement alors qu'un e-mail existant attend le temps du
# hachage bcrypt : cet écart de latence, mesurable à distance, permet à un
# attaquant de découvrir quels comptes existent sans jamais tenter un seul
# mot de passe.
HACHAGE_FACTICE = "$2b$12$aCd3VUqytmw01E9ad6vNKeq0uLsN2wuqHll9IUr1N48q/wi2gPEfW"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifier si un mot de passe en clair correspond à sa version hachée.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Générer un hachage bcrypt à partir d'un mot de passe en clair.
    """
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Générer un jeton d'accès JWT pour un sujet (par exemple, id_utilisateur ou email).
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
