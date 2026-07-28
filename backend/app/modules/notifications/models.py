from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from app.core.database import Base


class Notification(Base):
    """
    Notification destinée à un client ou à toute l'équipe admin. Pas de
    relationship ORM vers Client/Administrateur (même principe que
    AuditLog, voir audit.models) : une notification est un événement
    consulté directement via ses propres endpoints, pas une possession du
    client nécessitant un cascade delete dédié.
    """
    __tablename__ = "notifications"

    id_notification = Column(Integer, primary_key=True, index=True)
    # NULL pour une notification ADMIN (diffusée à toute l'équipe — voir
    # notifications.service.creer_notification_admins) ; sinon FK vers
    # utilisateurs.id_utilisateur du client destinataire.
    id_utilisateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=True, index=True)
    destinataire_type = Column(String, nullable=False, index=True)  # CLIENT, ADMIN
    type = Column(String, nullable=False)  # BIENVENUE, BUDGET_80, BUDGET_100, PAIEMENT_CONFIRME, ...
    titre = Column(String, nullable=False)
    message = Column(String, nullable=False)
    # Route frontend optionnelle vers laquelle naviguer au clic (ex: /dashboard).
    lien = Column(String, nullable=True)
    est_lue = Column(Boolean, default=False, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow, index=True)
