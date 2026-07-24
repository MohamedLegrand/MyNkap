from datetime import date as date_type, datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class OperationFinanciere:
    """
    Classe abstraite (mixin Python, non mappée à sa propre table) partagée
    par Transaction et Transfert. Chaque sous-classe possède sa propre table
    avec ces colonnes communes : le cahier des charges ne requiert jamais
    d'interroger Transaction et Transfert polymorphiquement ensemble, donc
    un héritage de table jointe (comme pour Utilisateur) serait une
    complexité inutile ici.
    """
    montant = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False, default=date_type.today)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(OperationFinanciere, Base):
    """
    Dépense ou revenu enregistré par le client. Jamais supprimée : toute
    correction s'effectue via une transaction d'annulation inverse
    (principe d'immuabilité, 6.2).
    """
    __tablename__ = "transactions"

    id_transaction = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_compte = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False, index=True)
    # Nullable : les écritures système (DEPOT_INITIAL, ANNULATION,
    # REMBOURSEMENT_DETTE, ENCAISSEMENT_CREANCE) n'ont pas de catégorie de
    # dépense/revenu — seules DEPENSE/REVENU en ont une pour le suivi budget.
    id_categorie = Column(Integer, ForeignKey("categories.id_categorie"), nullable=True, index=True)
    # DEPENSE, REVENU, DEPOT_INITIAL, ANNULATION, REMBOURSEMENT_DETTE, ENCAISSEMENT_CREANCE
    type = Column(String, nullable=False)
    est_recurrente = Column(Boolean, default=False)
    est_suspecte = Column(Boolean, default=False)
    id_transaction_annulee = Column(Integer, ForeignKey("transactions.id_transaction"), nullable=True)

    client = relationship("Client", back_populates="transactions")
    compte = relationship("CompteFinancier", foreign_keys=[id_compte])
    categorie = relationship("Categorie", back_populates="transactions")


class Transfert(OperationFinanciere, Base):
    """
    Mouvement atomique entre deux comptes du même client. Neutre sur le
    patrimoine net (ni dépense ni revenu, principe 6.5).
    """
    __tablename__ = "transferts"

    id_transfert = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_compte_source = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False)
    id_compte_destination = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False)

    client = relationship("Client", back_populates="transferts")
    compte_source = relationship("CompteFinancier", foreign_keys=[id_compte_source])
    compte_destination = relationship("CompteFinancier", foreign_keys=[id_compte_destination])


class TransactionRecurrente(Base):
    """
    Transaction planifiée automatiquement selon une fréquence donnée
    (fonctionnalité 11).
    """
    __tablename__ = "transactions_recurrentes"

    id_transaction_recurrente = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_compte = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False)
    id_categorie = Column(Integer, ForeignKey("categories.id_categorie"), nullable=False)
    montant = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # DEPENSE, REVENU
    description = Column(String, nullable=True)
    frequence = Column(String, nullable=False)  # HEBDOMADAIRE, MENSUELLE, TRIMESTRIELLE, ANNUELLE
    prochaine_execution = Column(Date, nullable=False)
    est_active = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="transactions_recurrentes")
    compte = relationship("CompteFinancier", foreign_keys=[id_compte])
    categorie = relationship("Categorie")


class TemplateTransaction(Base):
    """
    Modèle de transaction réutilisable en un tap (fonctionnalité 12).
    """
    __tablename__ = "templates_transaction"

    id_template = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_compte = Column(Integer, ForeignKey("comptes_financiers.id_compte"), nullable=False)
    id_categorie = Column(Integer, ForeignKey("categories.id_categorie"), nullable=False)
    nom = Column(String, nullable=False)
    montant = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # DEPENSE, REVENU
    description = Column(String, nullable=True)
    nombre_utilisations = Column(Integer, default=0)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="templates_transaction")
    compte = relationship("CompteFinancier", foreign_keys=[id_compte])
    categorie = relationship("Categorie")
