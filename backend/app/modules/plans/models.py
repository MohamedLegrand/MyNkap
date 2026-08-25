from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Plan(Base):
    """
    Plan tarifaire SaaS (GRATUIT, ESSENTIEL, PREMIUM). Aucune limite de
    quota (comptes/transactions illimités pour tous) — seule
    différenciation : l'accès à des fonctionnalités.
    """
    __tablename__ = "plans"

    id_plan = Column(Integer, primary_key=True, index=True)
    nom = Column(String, unique=True, nullable=False)  # GRATUIT, ESSENTIEL, PREMIUM
    prix_mensuel = Column(Numeric(14, 2), nullable=False, default=0)
    prix_annuel = Column(Numeric(14, 2), nullable=False, default=0)
    devise = Column(String, default="XAF", nullable=False)
    acces_dettes = Column(Boolean, default=False, nullable=False)
    acces_epargne = Column(Boolean, default=False, nullable=False)
    acces_recurrentes = Column(Boolean, default=False, nullable=False)
    acces_templates = Column(Boolean, default=False, nullable=False)
    acces_analyse = Column(Boolean, default=False, nullable=False)
    acces_jarvis = Column(Boolean, default=False, nullable=False)
    # Réservé au futur module Rapports (pas encore construit) : aucune
    # route ne vérifie ce flag pour l'instant.
    acces_rapport = Column(Boolean, default=False, nullable=False)
    acces_tontine = Column(Boolean, default=False, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)

    abonnements = relationship("Abonnement", back_populates="plan")
    prix_devises = relationship("PrixPlanDevise", back_populates="plan")


class PrixPlanDevise(Base):
    """
    Prix d'un plan payant (ESSENTIEL/PREMIUM) dans une devise donnée parmi
    celles couvertes par HR-Skills Pay (XAF, XOF, CDF, GNF, GMD). XAF et XOF
    partagent la même parité fixe (peg euro commun) : ce sont les mêmes
    montants que Plan.prix_mensuel/prix_annuel. CDF/GNF/GMD sont des
    estimations approximatives à valider côté business avant mise en
    production (voir la migration qui les insère).
    """
    __tablename__ = "prix_plan_devise"
    __table_args__ = (UniqueConstraint("id_plan", "devise", name="uq_prix_plan_devise"),)

    id_prix = Column(Integer, primary_key=True, index=True)
    id_plan = Column(Integer, ForeignKey("plans.id_plan"), nullable=False)
    devise = Column(String, nullable=False)
    prix_mensuel = Column(Numeric(14, 2), nullable=False)
    prix_annuel = Column(Numeric(14, 2), nullable=False)

    plan = relationship("Plan", back_populates="prix_devises")


class Abonnement(Base):
    """
    Abonnement d'un client à un plan tarifaire. Cycle de vie :
    ESSAI -> ACTIF -> EXPIRE/ANNULE (voir diagramme d'état-transition 7.1).
    """
    __tablename__ = "abonnements"

    id_abonnement = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), unique=True, nullable=False)
    id_plan = Column(Integer, ForeignKey("plans.id_plan"), nullable=False)
    date_debut = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_fin = Column(DateTime, nullable=True)
    # MENSUEL ou ANNUEL — None pour le plan GRATUIT (pas de cycle de
    # facturation, jamais d'expiration).
    cycle_facturation = Column(String, nullable=True)
    statut = Column(String, default="ESSAI", nullable=False)  # ESSAI, ACTIF, EXPIRE, ANNULE
    renouvellement_auto = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="abonnement")
    plan = relationship("Plan", back_populates="abonnements")


class PaiementAbonnement(Base):
    """
    Paiement Mobile Money (HR-Skills Pay) demandé pour souscrire à un plan
    payant. Dissocié de l'Abonnement lui-même car le paiement est
    asynchrone : le client doit encore confirmer via USSD/push sur son
    téléphone — le plan n'est réellement changé qu'une fois le statut
    SUCCESS confirmé (voir service.verifier_paiements_en_attente).
    """
    __tablename__ = "paiements_abonnement"

    id_paiement = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_plan_demande = Column(Integer, ForeignKey("plans.id_plan"), nullable=False)
    cycle_facturation = Column(String, nullable=False)  # MENSUEL, ANNUEL
    montant = Column(Numeric(14, 2), nullable=False)
    devise = Column(String, default="XAF", nullable=False)
    # Code pays HR-Skills Pay (ex. "CM", "SN") utilisé pour ce Cash-In —
    # traçabilité du rail Mobile Money employé, utile en support/debug.
    pays = Column(String, nullable=False, server_default="CM")
    reference_hrpay = Column(String, unique=True, nullable=False, index=True)
    statut = Column(String, default="PENDING", nullable=False)  # PENDING, SUCCESS, FAILED
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_confirmation = Column(DateTime, nullable=True)

    client = relationship("Client")
    plan_demande = relationship("Plan")
