from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Categorie(Base):
    """
    Catégorie personnalisée (dépense ou revenu) utilisée pour organiser les
    transactions et les budgets d'un client.
    """
    __tablename__ = "categories"

    id_categorie = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    type = Column(String, nullable=False)  # DEPENSE, REVENU
    icone = Column(String, nullable=True)
    couleur = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="categories")
    transactions = relationship("Transaction", back_populates="categorie")
    budgets = relationship("Budget", back_populates="categorie")


class Budget(Base):
    """
    Enveloppe budgétaire mensuelle par catégorie, avec alertes à 80% et 100%
    de consommation (voir principe de traçabilité et fonctionnalité 6).
    """
    __tablename__ = "budgets"

    id_budget = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_categorie = Column(Integer, ForeignKey("categories.id_categorie"), nullable=False)
    montant_limite = Column(Numeric(14, 2), nullable=False)
    mois = Column(Integer, nullable=False)
    annee = Column(Integer, nullable=False)
    alerte_80 = Column(Boolean, default=False)
    alerte_100 = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="budgets")
    categorie = relationship("Categorie", back_populates="budgets")
