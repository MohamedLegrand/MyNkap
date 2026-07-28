from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_admin, get_current_active_client
from app.modules.auth.models import Administrateur, Client
from app.modules.notifications import service
from app.modules.notifications.schemas import MarquerLuesOut, NonLuesCountOut, NotificationOut

router = APIRouter(tags=["Notifications"])


# --- Notifications Client ---

@router.get("/notifications", response_model=List[NotificationOut])
def lister_mes_notifications(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_notifications_client(db, client.id_client)


@router.get("/notifications/non-lues-count", response_model=NonLuesCountOut)
def compter_mes_notifications_non_lues(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return {"non_lues": service.compter_non_lues_client(db, client.id_client)}


@router.post("/notifications/{id_notification}/lire", response_model=NotificationOut)
def marquer_ma_notification_lue(
    id_notification: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    try:
        return service.marquer_lue_client(db, id_notification, client.id_client)
    except service.NotificationIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable.")


@router.post("/notifications/lire-tout", response_model=MarquerLuesOut)
def marquer_toutes_mes_notifications_lues(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return {"nb_marquees": service.marquer_toutes_lues_client(db, client.id_client)}


# --- Notifications Admin (diffusées à toute l'équipe) ---

@router.get("/admin/notifications", response_model=List[NotificationOut])
def lister_notifications_admin(
    db: Session = Depends(get_db),
    admin: Administrateur = Depends(get_current_active_admin),
):
    return service.lister_notifications_admin(db)


@router.get("/admin/notifications/non-lues-count", response_model=NonLuesCountOut)
def compter_notifications_admin_non_lues(
    db: Session = Depends(get_db),
    admin: Administrateur = Depends(get_current_active_admin),
):
    return {"non_lues": service.compter_non_lues_admin(db)}


@router.post("/admin/notifications/{id_notification}/lire", response_model=NotificationOut)
def marquer_notification_admin_lue(
    id_notification: int,
    db: Session = Depends(get_db),
    admin: Administrateur = Depends(get_current_active_admin),
):
    try:
        return service.marquer_lue_admin(db, id_notification)
    except service.NotificationIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable.")


@router.post("/admin/notifications/lire-tout", response_model=MarquerLuesOut)
def marquer_toutes_notifications_admin_lues(
    db: Session = Depends(get_db),
    admin: Administrateur = Depends(get_current_active_admin),
):
    return {"nb_marquees": service.marquer_toutes_lues_admin(db)}
