from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Rapport(Base):
    """
    Rapport financier PDF généré sur une période choisie par le client
    (fonctionnalité 10). `type` désigne le contenu du rapport (catalogue
    ci-dessous), pas le format — tout est PDF pour l'instant, Excel est
    différé.
    """
    __tablename__ = "rapports"

    id_rapport = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    # RELEVE_TRANSACTIONS, BILAN_BUDGETAIRE, DETTES_EPARGNE,
    # BILAN_FINANCIER, PREDICTIONS — voir rapports.service.CATALOGUE_RAPPORTS
    type = Column(String, nullable=False)
    periode_debut = Column(Date, nullable=False)
    periode_fin = Column(Date, nullable=False)
    chemin_fichier = Column(String, nullable=True)
    taille = Column(Integer, nullable=True)
    statut = Column(String, default="EN_COURS", nullable=False)  # EN_COURS, GENERE, ERREUR
    date_generation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="rapports")
