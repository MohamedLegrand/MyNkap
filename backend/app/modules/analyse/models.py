from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class AnalyseFinanciere(Base):
    """
    Analyse des habitudes financières d'un client sur une période donnée
    (fonctionnalité 20), avec un score financier personnel.
    """
    __tablename__ = "analyses_financieres"

    id_analyse = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    type = Column(String, nullable=False)  # HABITUDES, COMPORTEMENT, TENDANCES, COMPARAISON
    periode_debut = Column(Date, nullable=False)
    periode_fin = Column(Date, nullable=False)
    resultats = Column(JSON, nullable=True)
    score_financier = Column(Float, nullable=True)
    date_generation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="analyses_financieres")


class Prediction(Base):
    """
    Prédiction financière générée par JARVIS (dépenses futures, risque
    budgétaire, capacité d'épargne — fonctionnalité 19).
    """
    __tablename__ = "predictions"

    id_prediction = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    type = Column(String, nullable=False)  # DEPENSES_FUTURES, RISQUE_BUDGETAIRE, CAPACITE_EPARGNE
    periode_debut = Column(Date, nullable=False)
    periode_fin = Column(Date, nullable=False)
    montant_predit = Column(Float, nullable=True)
    niveau_confiance = Column(Float, nullable=True)
    recommandations = Column(String, nullable=True)
    date_generation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="predictions")
