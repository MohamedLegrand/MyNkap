from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from app.core.database import Base


class AuditLog(Base):
    """
    Trace de chaque action effectuée dans le système (qui, quoi, sur quelle
    ressource, avec quelles données avant/après). Exigence de traçabilité
    complète du cahier des charges — jamais modifiée ni supprimée.
    """
    __tablename__ = "audit_logs"

    id_audit = Column(Integer, primary_key=True, index=True)
    id_utilisateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    ressource = Column(String, nullable=False, index=True)
    id_ressource = Column(Integer, nullable=True)
    donnees_avant = Column(JSON, nullable=True)
    donnees_apres = Column(JSON, nullable=True)
    adresse_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow, index=True)


class Config(Base):
    """
    Paramètres de configuration applicative sous forme clé/valeur,
    modifiables sans redéploiement (ex : limites de plan, feature flags).
    """
    __tablename__ = "configs"

    id_config = Column(Integer, primary_key=True, index=True)
    cle = Column(String, unique=True, index=True, nullable=False)
    valeur = Column(String, nullable=False)
    type = Column(String, nullable=False, default="STRING")  # STRING, INT, BOOL, JSON
    description = Column(String, nullable=True)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
