from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.avis import service
from app.modules.avis.schemas import AvisOut, AvisPublicOut, CreerAvisRequest, InvitationAvisOut

router = APIRouter(tags=["Avis"])


@router.get("/avis/publics", response_model=List[AvisPublicOut])
def lister_avis_publics(db: Session = Depends(get_db)):
    """Avis publiés — consultable sans authentification, comme GET /plans
    (affiché sur la landing page)."""
    return service.lister_avis_publics(db)


@router.get("/avis/moi", response_model=Optional[AvisOut])
def obtenir_mon_avis(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Mon avis (s'il existe) et son statut de modération — null si le
    client n'en a encore soumis aucun."""
    return service.obtenir_mon_avis(db, client.id_client)


@router.post("/avis", response_model=AvisOut, status_code=status.HTTP_201_CREATED)
def creer_avis(
    payload: CreerAvisRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Soumet mon avis (note + commentaire) — toujours créé EN_ATTENTE, un
    admin doit le publier avant qu'il apparaisse sur la landing page."""
    try:
        return service.creer_avis(db, client.id_client, payload.note, payload.commentaire)
    except service.AvisDejaExistantError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vous avez déjà soumis un avis.",
        )


@router.get("/avis/invitation", response_model=InvitationAvisOut)
def obtenir_invitation_avis(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """
    Faut-il proposer activement (modale automatique à l'ouverture du
    tableau de bord) de laisser un avis maintenant ? Voir
    avis.service.doit_demander_avis pour les conditions.
    """
    return {"demander": service.doit_demander_avis(db, client)}


@router.post("/avis/reporter", status_code=status.HTTP_204_NO_CONTENT)
def reporter_avis(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Le client a choisi "Plus tard" — ne rien lui redemander avant 7 jours."""
    service.reporter_avis(db, client)
