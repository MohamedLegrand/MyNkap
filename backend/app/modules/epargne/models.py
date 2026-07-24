from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ObjectifEpargne(Base):
    """
    Objectif d'épargne avec compte épargne dédié créé automatiquement.
    L'épargne est un transfert vers ce compte, jamais une dépense
    (principe comptable de l'épargne, 6.8).
    """
    __tablename__ = "objectifs_epargne"

    id_objectif = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_compte_epargne = Column(Integer, ForeignKey("comptes_financiers.id_compte"), unique=True, nullable=False)
    nom = Column(String, nullable=False)
    montant_cible = Column(Float, nullable=False)
    date_echeance = Column(Date, nullable=True)
    statut = Column(String, default="EN_COURS", nullable=False)  # EN_COURS, ATTEINT, ABANDONNE
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="objectifs_epargne")
    compte_epargne = relationship("CompteFinancier", foreign_keys=[id_compte_epargne])
