from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ComptePrincipal(Base):
    """
    Compte agrégateur en lecture seule représentant la somme de tous les
    comptes financiers actifs d'un client. Jamais débité/crédité directement
    — recalculé automatiquement à chaque opération (voir principe 6.6).
    """
    __tablename__ = "comptes_principaux"

    id_compte_principal = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), unique=True, nullable=False)
    solde_total = Column(Float, default=0, nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    date_mise_a_jour = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="compte_principal")


class CompteFinancier(Base):
    """
    Compte financier d'un client (Mobile Money, bancaire, espèces, épargne).
    Le solde n'est mis à jour qu'atomiquement, via les services de transaction
    (jamais directement depuis un endpoint générique).
    """
    __tablename__ = "comptes_financiers"

    id_compte = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    type = Column(String, nullable=False)  # MOBILE_MONEY, BANCAIRE, ESPECES, EPARGNE
    solde = Column(Float, default=0, nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    est_actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="comptes_financiers")
