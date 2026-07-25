from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Categorie(Base):
    """
    Catégorie personnalisée (dépense ou revenu) utilisée pour organiser les
    transactions et les budgets d'un client.
    """
    __tablename__ = "categories"
    __table_args__ = (
        # Vérifiée en amont côté service pour un message d'erreur clair,
        # ET imposée ici en base pour rattraper une race condition entre
        # deux requêtes concurrentes (même raisonnement que Budget).
        UniqueConstraint("id_client", "nom", "type", name="uq_categories_client_nom_type"),
    )

    id_categorie = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    type = Column(String, nullable=False)  # DEPENSE, REVENU
    icone = Column(String, nullable=True)
    couleur = Column(String, nullable=True)
    # Désactivation logique — jamais de suppression réelle : Transaction et
    # Budget référencent id_categorie, un hard-delete casserait leur
    # historique (même principe que CompteFinancier/Budget).
    est_actif = Column(Boolean, default=True, nullable=False)
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
    __table_args__ = (
        # Un seul budget par catégorie et par mois — garde-fou applicatif
        # ET base de données (la vérification applicative seule est
        # vulnérable à une race condition entre deux requêtes concurrentes).
        UniqueConstraint(
            "id_client", "id_categorie", "mois", "annee",
            name="uq_budgets_client_categorie_mois_annee",
        ),
    )

    id_budget = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_categorie = Column(Integer, ForeignKey("categories.id_categorie"), nullable=False)
    montant_limite = Column(Numeric(14, 2), nullable=False)
    mois = Column(Integer, nullable=False)
    annee = Column(Integer, nullable=False)
    alerte_80 = Column(Boolean, default=False)
    alerte_100 = Column(Boolean, default=False)
    # Désactivation logique — jamais de suppression réelle, même principe
    # que CompteFinancier (l'historique des alertes en AuditLog resterait
    # sinon orphelin d'un budget réellement supprimé).
    est_actif = Column(Boolean, default=True, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="budgets")
    categorie = relationship("Categorie", back_populates="budgets")
