import json
from typing import Any, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog, Config


def enregistrer_action(
    db: Session,
    id_utilisateur: int,
    action: str,
    ressource: str,
    id_ressource: Optional[int] = None,
    donnees_avant: Optional[dict] = None,
    donnees_apres: Optional[dict] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """
    Enregistre une entrée d'audit pour une action effectuée sur une ressource.
    """
    entry = AuditLog(
        id_utilisateur=id_utilisateur,
        action=action,
        ressource=ressource,
        id_ressource=id_ressource,
        donnees_avant=donnees_avant,
        donnees_apres=donnees_apres,
        adresse_ip=request.client.host if request is not None and request.client else None,
        user_agent=request.headers.get("user-agent") if request is not None else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# --- Configuration clé/valeur ---

def _deserialiser(config: Config) -> Any:
    if config.type == "INT":
        return int(config.valeur)
    if config.type == "BOOL":
        return config.valeur.lower() in ("true", "1", "yes")
    if config.type == "JSON":
        return json.loads(config.valeur)
    return config.valeur


def get_config(db: Session, cle: str, default: Any = None) -> Any:
    """
    Récupère une valeur de configuration par sa clé, désérialisée selon son
    type déclaré. Retourne `default` si la clé n'existe pas.
    """
    config = db.query(Config).filter(Config.cle == cle).first()
    if config is None:
        return default
    return _deserialiser(config)


def set_config(db: Session, cle: str, valeur: Any, type_: str = "STRING", description: Optional[str] = None) -> Config:
    """
    Crée ou met à jour une valeur de configuration.
    """
    serialisee = json.dumps(valeur) if type_ == "JSON" else str(valeur)

    config = db.query(Config).filter(Config.cle == cle).first()
    if config is None:
        config = Config(cle=cle, valeur=serialisee, type=type_, description=description)
        db.add(config)
    else:
        config.valeur = serialisee
        config.type = type_
        if description is not None:
            config.description = description

    db.commit()
    db.refresh(config)
    return config
