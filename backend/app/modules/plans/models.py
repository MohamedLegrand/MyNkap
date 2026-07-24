from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Plan(Base):
    """
    Plan tarifaire SaaS (FREE, PRO, BUSINESS) définissant les limites
    d'usage et les accès fonctionnels associés.
    """
    __tablename__ = "plans"

    id_plan = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)  # FREE, PRO, BUSINESS
    prix = Column(Float, nullable=False, default=0)
    devise = Column(String, default="XAF", nullable=False)
    max_comptes = Column(Integer, nullable=False)
    max_transactions = Column(Integer, nullable=False)
    acces_jarvis = Column(Boolean, default=False)
    acces_prediction = Column(Boolean, default=False)
    acces_rapport = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.utcnow)

    abonnements = relationship("Abonnement", back_populates="plan")


class Abonnement(Base):
    """
    Abonnement d'un client à un plan tarifaire. Cycle de vie :
    ESSAI -> ACTIF -> EXPIRE/ANNULE (voir diagramme d'état-transition 7.1).
    """
    __tablename__ = "abonnements"

    id_abonnement = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), unique=True, nullable=False)
    id_plan = Column(Integer, ForeignKey("plans.id_plan"), nullable=False)
    date_debut = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_fin = Column(DateTime, nullable=True)
    statut = Column(String, default="ESSAI", nullable=False)  # ESSAI, ACTIF, EXPIRE, ANNULE
    renouvellement_auto = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="abonnement")
    plan = relationship("Plan", back_populates="abonnements")
