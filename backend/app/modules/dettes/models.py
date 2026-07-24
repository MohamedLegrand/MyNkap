from datetime import datetime
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
    montant_rembourse = Column(Numeric(14, 2), default=0, nullable=False)
    personne_impliquee = Column(String, nullable=True)
    date_echeance = Column(Date, nullable=True)
    # EN_COURS, PARTIELLEMENT_REMBOURSE, SOLDE, EN_RETARD
    statut = Column(String, default="EN_COURS", nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="dettes")
    compte = relationship("CompteFinancier", foreign_keys=[id_compte])
    transaction_origine = relationship("Transaction", foreign_keys=[id_transaction_origine])
