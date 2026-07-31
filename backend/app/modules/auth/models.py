from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Utilisateur(Base):
    """
    Modèle de base pour tous les utilisateurs du système (polymorphisme joint).
    """
    __tablename__ = "utilisateurs"

    id_utilisateur = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    mot_de_passe = Column(String, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    est_actif = Column(Boolean, default=True)
    type = Column(String(50), nullable=False)

    # Double authentification par code à 6 chiffres envoyé par e-mail
    # (Brevo) à chaque connexion — sur Utilisateur (pas Client) pour
    # s'appliquer uniformément aux clients ET aux administrateurs.
    otp_code = Column(String(6), nullable=True)
    otp_expiration = Column(DateTime, nullable=True)

    # Suivi des tentatives de connexion échouées (mot de passe OU code OTP
    # incorrect) — remis à zéro dès une connexion réussie. Sert à notifier
    # le client au-delà d'un seuil (voir auth.services.SEUIL_ALERTE_TENTATIVES)
    # sans le renotifier à chaque nouvel échec tant que le seuil reste
    # dépassé (même principe que Budget.alerte_80/alerte_100).
    tentatives_echouees = Column(Integer, default=0, nullable=False)
    alerte_tentatives_envoyee = Column(Boolean, default=False, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "utilisateur",
    }

class Client(Utilisateur):
    """
    Modèle représentant un Client (acteur principal effectuant ses suivis financiers).
    """
    __tablename__ = "clients"

    id_client = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    # Récupération du mot de passe oublié
    reset_password_token = Column(String, nullable=True, unique=True)
    reset_password_expires = Column(DateTime, nullable=True)

    # Relation 1-à-1 avec le profil utilisateur
    profile = relationship("Profile", back_populates="client", uselist=False, cascade="all, delete-orphan")

    # Relation 1-à-N avec les Refresh Tokens de session
    refresh_tokens = relationship("RefreshToken", back_populates="client", cascade="all, delete-orphan")

    # Relations 1-à-1
    compte_principal = relationship("ComptePrincipal", back_populates="client", uselist=False, cascade="all, delete-orphan")
    abonnement = relationship("Abonnement", back_populates="client", uselist=False, cascade="all, delete-orphan")

    # Relations 1-à-N (composition : supprimées avec le client, principe 6.2 du cahier des charges)
    comptes_financiers = relationship("CompteFinancier", back_populates="client", cascade="all, delete-orphan")
    categories = relationship("Categorie", back_populates="client", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="client", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="client", cascade="all, delete-orphan", foreign_keys="Transaction.id_client")
    transferts = relationship("Transfert", back_populates="client", cascade="all, delete-orphan")
    transactions_recurrentes = relationship("TransactionRecurrente", back_populates="client", cascade="all, delete-orphan")
    templates_transaction = relationship("TemplateTransaction", back_populates="client", cascade="all, delete-orphan")
    objectifs_epargne = relationship("ObjectifEpargne", back_populates="client", cascade="all, delete-orphan")
    dettes = relationship("Dette", back_populates="client", cascade="all, delete-orphan")
    rapports = relationship("Rapport", back_populates="client", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="client", cascade="all, delete-orphan")
    actions_ia = relationship("ActionIA", back_populates="client", cascade="all, delete-orphan")
    analyses_financieres = relationship("AnalyseFinanciere", back_populates="client", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="client", cascade="all, delete-orphan")

    __mapper_args__ = {
        "polymorphic_identity": "client",
    }

class Administrateur(Utilisateur):
    """
    Modèle représentant un Administrateur de la plateforme MyNkap.
    """
    __tablename__ = "administrateurs"

    id_administrateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    niveau_acces = Column(Integer, default=1)

    __mapper_args__ = {
        "polymorphic_identity": "administrateur",
    }

class Profile(Base):
    """
    Modèle contenant les préférences et métadonnées de profil d'un Client.
    """
    __tablename__ = "profiles"

    id_profile = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), unique=True, nullable=False)
    avatar = Column(String, nullable=True)
    devise = Column(String, default="XAF", nullable=False)
    langue = Column(String, default="FR", nullable=False)

    client = relationship("Client", back_populates="profile")

class RefreshToken(Base):
    """
    Modèle représentant les jetons de rafraîchissement pour la persistance des sessions.
    """
    __tablename__ = "refresh_tokens"

    id_refresh_token = Column(Integer, primary_key=True, index=True)
    # Référence n'importe quel Utilisateur (Client OU Administrateur) — pas
    # seulement Client. Corrige un bug reel : /auth/login appelle
    # creer_refresh_token() pour tout Utilisateur authentifie, mais la
    # contrainte pointait avant uniquement vers clients.id_client, ce qui
    # provoquait un IntegrityError Postgres (500 non gere) a chaque
    # connexion d'un administrateur, puisqu'il n'a pas de ligne dans
    # clients (verifie contre Postgres reel).
    id_client = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    # Empreinte SHA-256 du jeton, jamais le jeton en clair (voir
    # auth.services._hasher_token) — une fuite de la base ne donne plus un
    # accès direct de 8 jours à un compte, même principe que le hachage
    # bcrypt des mots de passe (une empreinte rapide suffit ici : le jeton a
    # déjà 256 bits d'entropie aléatoire, contrairement à un mot de passe
    # choisi par l'utilisateur).
    token_hash = Column(String, unique=True, index=True, nullable=False)
    date_expiration = Column(DateTime, nullable=False)
    est_revoque = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.utcnow)

    # primaryjoin explicite : la FK ci-dessus pointe vers `utilisateurs`,
    # pas directement vers `clients` (heritage par jointure) — SQLAlchemy
    # ne peut plus inferer seul la jointure entre RefreshToken et Client.
    client = relationship(
        "Client",
        back_populates="refresh_tokens",
        primaryjoin="foreign(RefreshToken.id_client) == Client.id_client",
    )
