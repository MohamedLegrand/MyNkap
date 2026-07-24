from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Dette(Base):
    """
    Dette reçue (passif) ou créance accordée (actif). Ni l'une ni l'autre
    n'est une dépense/un revenu direct — seuls les mouvements de
    remboursement/encaissement affectent réellement la trésorerie
    (principe comptable des dettes, 6.7).
    """
    __tablename__ = "dettes"

    id_dette = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_transaction_origine = Column(Integer, ForeignKey("transactions.id_transaction"), nullable=True)
    id_compte = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False)
    nom = Column(String, nullable=False)
    type = Column(String, nullable=False)  # DETTE, CREANCE
    montant_total = Column(Numeric(14, 2), nullable=False)
    # Toujours dérivé de la somme des transactions REMBOURSEMENT_DETTE/
    # ENCAISSEMENT_CREANCE liées (via Transaction.id_dette) — jamais
    # incrémenté directement, pour éviter toute désynchronisation entre
    # l'affiché et le réellement survenu.
    montant_rembourse = Column(Numeric(14, 2), default=0, nullable=False)
    personne_impliquee = Column(String, nullable=True)
    date_echeance = Column(Date, nullable=True)
    # EN_COURS, PARTIELLEMENT_REMBOURSE, SOLDE, PERTE (PERTE : manuel,
    # créances uniquement). EN_RETARD n'est jamais stocké ici : c'est un
    # état dérivé à la volée depuis date_echeance (get_jours_avant_echeance).
    statut = Column(String, default="EN_COURS", nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="dettes")
    compte = relationship("CompteFinancier", foreign_keys=[id_compte])
    transaction_origine = relationship("Transaction", foreign_keys=[id_transaction_origine])
    # Toutes les transactions liées à cette dette : l'origine ET chaque
    # remboursement/encaissement (distinct de transaction_origine qui ne
    # pointe que sur la toute première).
    transactions_liees = relationship(
        "Transaction", foreign_keys="Transaction.id_dette", back_populates="dette"
    )

    def get_montant_restant(self) -> Decimal:
        return self.montant_total - self.montant_rembourse

    def get_pourcentage_rembourse(self) -> float:
        if self.montant_total == 0:
            return 0.0
        return float(self.montant_rembourse / self.montant_total * 100)

    def est_solde(self) -> bool:
        return self.statut == "SOLDE"

    def marquer_comme_solde(self) -> None:
        self.statut = "SOLDE"

    def get_jours_avant_echeance(self) -> Optional[int]:
        """Négatif si l'échéance est dépassée — c'est cette valeur qui sert
        à dériver l'affichage "EN_RETARD" côté client, sans jamais stocker
        cet état dans `statut`."""
        if self.date_echeance is None:
            return None
        return (self.date_echeance - date.today()).days

    def get_impact_patrimoine_net(self) -> Decimal:
        """
        Impact signé de cette dette/créance sur le patrimoine net (principe
        6.9) : -montant_restant si DETTE (passif), +montant_restant si
        CREANCE (actif). Une créance classée PERTE cesse de compter comme
        actif — c'est ce qui fait réellement chuter le patrimoine net au
        moment où la perte est constatée.
        """
        if self.statut == "PERTE":
            return Decimal("0")
        restant = self.get_montant_restant()
        return -restant if self.type == "DETTE" else restant
