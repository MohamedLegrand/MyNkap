from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# --- Schémas pour les profils ---
class ProfileOut(BaseModel):
    id_profile: int
    avatar: Optional[str] = None
    devise: str
    langue: str

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    avatar: Optional[str] = None
    devise: Optional[str] = None
    langue: Optional[str] = None

# --- Schémas pour l'inscription ---
class UserRegister(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(..., min_length=6)
    first_name: str
    last_name: str
    phone: str

# --- Schémas pour la connexion ---
class UserLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# --- Schémas de sortie pour les utilisateurs ---
class ClientOut(BaseModel):
    id_client: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    est_actif: bool
    date_creation: datetime
    profile: Optional[ProfileOut] = None

    class Config:
        from_attributes = True

class AdminOut(BaseModel):
    id_administrateur: int
    email: EmailStr
    username: str
    niveau_acces: int
    est_actif: bool
    date_creation: datetime

    class Config:
        from_attributes = True

# --- Schémas pour la récupération de mot de passe ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    nouveau_mot_de_passe: str = Field(..., min_length=6)
