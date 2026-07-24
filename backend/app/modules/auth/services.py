import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.modules.auth.models import Utilisateur, Client, Profile, RefreshToken
from app.modules.auth.schemas import UserRegister, UserLogin, ResetPasswordRequest

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
        username=client_in.username,
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
    db.commit()
    db.refresh(db_client)
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

def revoquer_refresh_token(db: Session, token: str) -> bool:
    """
    Révoque un jeton de rafraîchissement en base de données.
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db_token.est_revoque = True
        db.commit()
        return True
    return False

# --- Services de récupération de mot de passe ---

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
    
    # Simulation d'envoi d'e-mail (Pour le dev, on l'affiche dans les logs de la console)
    print(f"\n[E-MAIL SIMULATION] Réinitialisation demandée pour {email}")
    print(f"[E-MAIL SIMULATION] Token : {reset_token}\n")
    
    return reset_token

def reinitialiser_mot_de_passe(db: Session, reset_in: ResetPasswordRequest) -> bool:
    """
    Valide le jeton de récupération et applique le nouveau mot de passe.
    """
    client = db.query(Client).filter(
        Client.reset_password_token == reset_in.token,
        Client.reset_password_expires > datetime.utcnow()
    ).first()
    
    if not client:
        return False
    
    # Mise à jour du mot de passe
    client.mot_de_passe = get_password_hash(reset_in.nouveau_mot_de_passe)
    # Nettoyage du token
    client.reset_password_token = None
    client.reset_password_expires = None
    
    db.commit()
    return True
