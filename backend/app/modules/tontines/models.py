from datetime import datetime, date as date_type
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tontine(Base):
    """
    Cercle d'épargne rotatif (tontine/njangi) : un groupe de membres cotise
    à intervalle régulier, et la cagnotte complète est remise à tour de
    rôle à chacun. Volontairement un simple carnet de suivi — aucune
    Transaction ni CompteFinancier n'est généré, jamais aucun mouvement
    réel n'est simulé (voir MembreTontine/CotisationTour) : l'argent
    circule en vrai entre les membres, hors de l'application, MyNkap n'en
    a jamais la garde. Portée par un seul client (l'organisateur/
    trésorier) : les autres membres n'ont pas besoin d'un compte MyNkap.
    """
    __tablename__ = "tontines"

    id_tontine = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    montant_cotisation = Column(Numeric(14, 2), nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    # HEBDOMADAIRE ou MENSUELLE — détermine l'espacement entre les tours
    # (voir service._calculer_date_tour).
    frequence = Column(String, nullable=False)
    date_debut = Column(Date, nullable=False, default=date_type.today)
    # ACTIVE, TERMINEE (tous les tours clôturés), ANNULEE (manuel)
    statut = Column(String, default="ACTIVE", nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="tontines")
    membres = relationship(
        "MembreTontine", back_populates="tontine", cascade="all, delete-orphan", order_by="MembreTontine.ordre"
    )
    tours = relationship(
        "TourTontine", back_populates="tontine", cascade="all, delete-orphan", order_by="TourTontine.numero"
    )


class MembreTontine(Base):
    """
    Participant d'une tontine — simple fiche nominative (comme
    Dette.personne_impliquee), pas nécessairement un client MyNkap."""
    __tablename__ = "membres_tontine"

    id_membre = Column(Integer, primary_key=True, index=True)
    id_tontine = Column(Integer, ForeignKey("tontines.id_tontine"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    telephone = Column(String, nullable=True)
    # Position dans la rotation (1-based) : détermine à quel numéro de tour
    # ce membre reçoit la cagnotte.
    ordre = Column(Integer, nullable=False)

    tontine = relationship("Tontine", back_populates="membres")


class TourTontine(Base):
    """Un tour de rotation : un membre bénéficiaire, une échéance, et une
    cotisation attendue de la part de chaque membre du groupe."""
    __tablename__ = "tours_tontine"

    id_tour = Column(Integer, primary_key=True, index=True)
    id_tontine = Column(Integer, ForeignKey("tontines.id_tontine"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    id_membre_beneficiaire = Column(Integer, ForeignKey("membres_tontine.id_membre"), nullable=False)
    date_prevue = Column(Date, nullable=False)
    # A_VENIR, EN_COURS (le tour actif, un seul à la fois), TERMINE
    statut = Column(String, default="A_VENIR", nullable=False)

    tontine = relationship("Tontine", back_populates="tours")
    membre_beneficiaire = relationship("MembreTontine", foreign_keys=[id_membre_beneficiaire])
    cotisations = relationship(
        "CotisationTour", back_populates="tour", cascade="all, delete-orphan", order_by="CotisationTour.id_membre"
    )


class CotisationTour(Base):
    """Cotisation attendue d'un membre donné pour un tour donné — coché
    manuellement par l'organisateur au fur et à mesure des versements
    réels (cash/Mobile Money) qui ont lieu hors de l'application."""
    __tablename__ = "cotisations_tour"

    id_cotisation = Column(Integer, primary_key=True, index=True)
    id_tour = Column(Integer, ForeignKey("tours_tontine.id_tour"), nullable=False, index=True)
    id_membre = Column(Integer, ForeignKey("membres_tontine.id_membre"), nullable=False, index=True)
    est_versee = Column(Boolean, default=False, nullable=False)
    date_versement = Column(DateTime, nullable=True)

    tour = relationship("TourTontine", back_populates="cotisations")
    membre = relationship("MembreTontine", foreign_keys=[id_membre])
