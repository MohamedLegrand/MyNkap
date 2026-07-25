from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.jarvis import service
from app.modules.jarvis.schemas import (
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
    MessageCreate,
    MessageOut,
)

router = APIRouter(prefix="/jarvis", tags=["JARVIS"])


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def creer_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.creer_conversation(db, client.id_client, payload.titre)


@router.get("/conversations", response_model=List[ConversationOut])
def lister_conversations(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_conversations(db, client.id_client)


@router.get("/conversations/{id_conversation}", response_model=ConversationDetailOut)
def obtenir_conversation(
    id_conversation: UUID,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    conversation = service.obtenir_conversation_du_client(db, id_conversation, client.id_client)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return conversation


@router.delete("/conversations/{id_conversation}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_conversation(
    id_conversation: UUID,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Suppression réelle — une conversation n'est pas un enregistrement
    financier (voir service.supprimer_conversation)."""
    try:
        service.supprimer_conversation(db, id_conversation, client.id_client)
    except service.ConversationIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")


@router.post("/conversations/{id_conversation}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
def poser_question(
    request: Request,
    id_conversation: UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Pose une question à JARVIS. La réponse s'appuie uniquement sur la
    situation financière réelle du client (lecture seule, aucune action
    n'est exécutée dans cette version)."""
    try:
        return service.poser_question(db, client.id_client, id_conversation, payload.contenu)
    except service.ConversationIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    except service.ServiceIAIndisponibleError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JARVIS est momentanément indisponible, veuillez réessayer.",
        )
