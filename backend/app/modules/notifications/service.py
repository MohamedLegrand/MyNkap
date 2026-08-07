from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification


class NotificationIntrouvableError(Exception):
    """La notification demandée n'existe pas ou n'appartient pas au destinataire."""


def creer_notification_client(
    db: Session, id_client: int, type_: str, titre: str, message: str, lien: Optional[str] = None
) -> Notification:
    notification = Notification(
        id_utilisateur=id_client,
        destinataire_type="CLIENT",
        type=type_,
        titre=titre,
        message=message,
        lien=lien,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def creer_notification_admins(
    db: Session, type_: str, titre: str, message: str, lien: Optional[str] = None
) -> Notification:
    """
    Une seule ligne diffusée à toute l'équipe admin (id_utilisateur NULL),
    plutôt qu'une ligne par admin existant — plus simple, et cohérent avec
    l'AuditLog qui est lui aussi une vue partagée entre admins. Conséquence
    acceptée : marquer cette notification comme lue la marque lue pour
    toute l'équipe, pas seulement l'admin qui l'a ouverte.
    """
    notification = Notification(
        id_utilisateur=None,
        destinataire_type="ADMIN",
        type=type_,
        titre=titre,
        message=message,
        lien=lien,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def lister_notifications_client(db: Session, id_client: int, limit: int = 50) -> List[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.destinataire_type == "CLIENT", Notification.id_utilisateur == id_client)
        .order_by(Notification.date_creation.desc())
        .limit(limit)
        .all()
    )


def lister_notifications_admin(db: Session, limit: int = 50) -> List[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.destinataire_type == "ADMIN")
        .order_by(Notification.date_creation.desc())
        .limit(limit)
        .all()
    )


def compter_non_lues_client(db: Session, id_client: int) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.destinataire_type == "CLIENT",
            Notification.id_utilisateur == id_client,
            Notification.est_lue.is_(False),
        )
        .count()
    )


def compter_non_lues_admin(db: Session) -> int:
    return (
        db.query(Notification)
        .filter(Notification.destinataire_type == "ADMIN", Notification.est_lue.is_(False))
        .count()
    )


def marquer_lue_client(db: Session, id_notification: int, id_client: int) -> Notification:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id_notification == id_notification,
            Notification.destinataire_type == "CLIENT",
            Notification.id_utilisateur == id_client,
        )
        .first()
    )
    if notification is None:
        raise NotificationIntrouvableError()
    notification.est_lue = True
    db.commit()
    db.refresh(notification)
    return notification


def marquer_lue_admin(db: Session, id_notification: int) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.id_notification == id_notification, Notification.destinataire_type == "ADMIN")
        .first()
    )
    if notification is None:
        raise NotificationIntrouvableError()
    notification.est_lue = True
    db.commit()
    db.refresh(notification)
    return notification


def marquer_toutes_lues_client(db: Session, id_client: int) -> int:
    nb = (
        db.query(Notification)
        .filter(
            Notification.destinataire_type == "CLIENT",
            Notification.id_utilisateur == id_client,
            Notification.est_lue.is_(False),
        )
        .update({"est_lue": True})
    )
    db.commit()
    return nb


def marquer_toutes_lues_admin(db: Session) -> int:
    nb = (
        db.query(Notification)
        .filter(Notification.destinataire_type == "ADMIN", Notification.est_lue.is_(False))
        .update({"est_lue": True})
    )
    db.commit()
    return nb


def supprimer_client(db: Session, id_notification: int, id_client: int) -> None:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id_notification == id_notification,
            Notification.destinataire_type == "CLIENT",
            Notification.id_utilisateur == id_client,
        )
        .first()
    )
    if notification is None:
        raise NotificationIntrouvableError()
    db.delete(notification)
    db.commit()


def supprimer_toutes_client(db: Session, id_client: int) -> int:
    nb = (
        db.query(Notification)
        .filter(Notification.destinataire_type == "CLIENT", Notification.id_utilisateur == id_client)
        .delete()
    )
    db.commit()
    return nb


def supprimer_admin(db: Session, id_notification: int) -> None:
    notification = (
        db.query(Notification)
        .filter(Notification.id_notification == id_notification, Notification.destinataire_type == "ADMIN")
        .first()
    )
    if notification is None:
        raise NotificationIntrouvableError()
    db.delete(notification)
    db.commit()


def supprimer_toutes_admin(db: Session) -> int:
    nb = db.query(Notification).filter(Notification.destinataire_type == "ADMIN").delete()
    db.commit()
    return nb
