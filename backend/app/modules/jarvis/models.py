import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, JSON, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base


class Conversation(Base):
    """
    Fil de discussion persistant entre un client et l'assistant IA.
    """
    __tablename__ = "conversations"

    id_conversation = Column(Uuid, primary_key=True, default=uuid.uuid4)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    titre = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_dernier_message = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.date_creation",
    )


class Message(Base):
    """
    Message échangé au sein d'une Conversation (question du client ou
    réponse de l'assistant IA).
    """
    __tablename__ = "messages"

    id_message = Column(Uuid, primary_key=True, default=uuid.uuid4)
    id_conversation = Column(Uuid, ForeignKey("conversations.id_conversation"), nullable=False, index=True)
    contenu = Column(String, nullable=False)
    type = Column(String, nullable=False)  # QUESTION, REPONSE
    canal = Column(String, default="TEXTE", nullable=False)  # TEXTE, VOCAL
    peut_se_permettre = Column(Boolean, nullable=True)
    # Numeric (pas Float) : même principe que partout ailleurs dans le
    # projet, l'argent n'est jamais sujet aux imprécisions IEEE-754.
    montant_suggere = Column(Numeric(14, 2), nullable=True)
    conseil_supplementaire = Column(String, nullable=True)
    # Renseignés uniquement sur les messages de type REPONSE quand la
    # question du client était ambiguë : JARVIS repose la question au lieu
    # de deviner, avec éventuellement des choix cliquables (QCM).
    necessite_clarification = Column(Boolean, default=False, nullable=False)
    options_suggerees = Column(JSON, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    actions = relationship("ActionIA", back_populates="message", cascade="all, delete-orphan")


class ActionIA(Base):
    """
    Action proposée par l'assistant IA (créer une transaction ou un compte)
    et exécutée uniquement après confirmation explicite du client — JARVIS
    ne modifie jamais de donnée financière de sa propre initiative, voir
    jarvis.service.confirmer_action.
    """
    __tablename__ = "actions_ia"

    id_action = Column(Uuid, primary_key=True, default=uuid.uuid4)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_message = Column(Uuid, ForeignKey("messages.id_message"), nullable=False)
    type_action = Column(String, nullable=False)  # CREER_TRANSACTION, CREER_COMPTE
    # Paramètres de l'action, sérialisés en JSON (id_compte, montant...) —
    # jamais exécutés tels quels : revalidés via les schémas Pydantic des
    # modules cibles au moment de la confirmation (voir service.confirmer_action).
    donnees_cible = Column(String, nullable=True)
    # Résumé lisible ("Dépense de 2000 XAF (Alimentation) sur MOMO"), calculé
    # une fois à la proposition à partir des vrais noms de compte/catégorie
    # — jamais reconstruit depuis le texte libre du fournisseur IA, pour ne
    # jamais afficher un nom halluciné au client.
    resume = Column(String, nullable=False)
    confirmation_token = Column(String, nullable=True, unique=True)
    statut = Column(String, default="EN_ATTENTE", nullable=False)  # EN_ATTENTE, EXECUTE, ANNULE
    date_expiration = Column(DateTime, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="actions_ia")
    message = relationship("Message", back_populates="actions")
