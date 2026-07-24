import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Uuid
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
    montant_suggere = Column(Float, nullable=True)
    conseil_supplementaire = Column(String, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class ActionIA(Base):
    """
    Action proposée par l'assistant IA (créer/modifier/supprimer une
    ressource) et exécutée uniquement après confirmation explicite du
    client via un confirmation_token à usage unique.
    """
    __tablename__ = "actions_ia"

    id_action = Column(Uuid, primary_key=True, default=uuid.uuid4)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    id_message = Column(Uuid, ForeignKey("messages.id_message"), nullable=False)
    type_action = Column(String, nullable=False)  # CREER, MODIFIER, SUPPRIMER
    donnees_cible = Column(String, nullable=True)
    confirmation_token = Column(String, nullable=True, unique=True)
    statut = Column(String, default="EN_ATTENTE", nullable=False)  # EN_ATTENTE, CONFIRME, ANNULE, EXECUTE
    date_expiration = Column(DateTime, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="actions_ia")
    message = relationship("Message")
