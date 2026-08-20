from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base


class Avis(Base):
    """
    Avis d'un client sur MyNkap, affiché publiquement sur la landing page
    une fois modéré. Un seul avis par client (id_client unique) — pas de
    resoumission en boucle. Jamais publié directement : un client crée
    toujours en EN_ATTENTE, seul un admin (niveau 2+) peut passer à PUBLIE
    ou REJETE (voir avis.service et admin.service.moderer_avis_admin) —
    même principe que les paiements en litige, rien de visible
    publiquement ne part sans contrôle humain.
    """
    __tablename__ = "avis"

    id_avis = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False, unique=True, index=True)
    note = Column(Integer, nullable=False)  # 1 à 5
    commentaire = Column(Text, nullable=False)
    statut = Column(String, default="EN_ATTENTE", nullable=False)  # EN_ATTENTE, PUBLIE, REJETE
    date_creation = Column(DateTime, default=datetime.utcnow)
    date_moderation = Column(DateTime, nullable=True)
