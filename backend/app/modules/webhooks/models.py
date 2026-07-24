from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class WebhookEvent(Base):
    """
    Événement sortant à notifier à un service externe (ex : changement de
    plan, action IA exécutée), avec re-tentatives en cas d'échec.
    """
    __tablename__ = "webhook_events"

    id_webhook = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, index=True)
    type_event = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    statut = Column(String, default="EN_ATTENTE", nullable=False)  # EN_ATTENTE, ENVOYE, ECHEC
    nombre_tentatives = Column(Integer, default=0)
    date_prochain_essai = Column(DateTime, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="webhook_events")
