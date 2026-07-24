from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
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
    solde_total = Column(Numeric(14, 2), default=0, nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    date_mise_a_jour = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="compte_principal")


class CompteFinancier(Base):
    """
    Compte financier d'un client (Mobile Money, bancaire, espèces, épargne).
    Le solde n'est mis à jour qu'atomiquement, via les services de transaction
    (jamais directement depuis un endpoint générique).

    - `solde` est en Numeric (pas Float) : l'argent ne doit jamais être sujet
      aux imprécisions d'arrondi IEEE-754.
    - Une contrainte CHECK en base empêche un solde négatif même si un futur
      bug applicatif contournait les fonctions crediter()/debiter() dédiées —
      la discipline de code seule ne suffit pas comme garde-fou.
    """
    __tablename__ = "comptes_financiers"
    __table_args__ = (
        CheckConstraint("solde >= 0", name="ck_comptes_financiers_solde_non_negatif"),
    )

    id_compte = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    type = Column(String, nullable=False)  # MOBILE_MONEY, BANCAIRE, ESPECES, EPARGNE
    solde = Column(Numeric(14, 2), default=0, nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    est_actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="comptes_financiers")

    def est_suffisant(self, montant: Decimal) -> bool:
        """Vrai si le solde actuel couvre le montant demandé (vérifié avant
        toute dépense)."""
        return self.solde >= montant
