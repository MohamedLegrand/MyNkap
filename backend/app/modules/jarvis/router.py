import base64
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.jarvis import service
from app.modules.jarvis.schemas import (
    ActionIAOut,
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
    MessageCreate,
    MessageOut,
    MessageVocalOut,
)
from app.modules.plans.dependencies import exiger_fonctionnalite
from app.modules.transactions.service import (
    CategorieIntrouvableError,
    CompteIntrouvableError,
    SoldeInsuffisantError,
)

router = APIRouter(
    prefix="/jarvis",
    tags=["JARVIS"],
    dependencies=[Depends(exiger_fonctionnalite("acces_jarvis"))],
)


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


@router.post(
    "/conversations/{id_conversation}/messages/vocal",
    response_model=MessageVocalOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
def poser_question_vocale(
    request: Request,
    id_conversation: UUID,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """
    Conversation orale de bout en bout : la voix du client est transcrite
    (Whisper/Groq), passe par le même raisonnement financier que le chat
    écrit, puis la réponse est synthétisée en voix (Gemini). Rate limit
    plus strict qu'en texte : chaque appel déclenche trois requêtes vers
    des fournisseurs externes (transcription, raisonnement, synthèse).
    """
    try:
        message, audio_reponse = service.poser_question_vocale(
            db,
            client.id_client,
            id_conversation,
            audio.file.read(),
            audio.filename or "audio.webm",
            audio.content_type or "audio/webm",
        )
    except service.ConversationIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    except service.ServiceIAIndisponibleError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JARVIS est momentanément indisponible, veuillez réessayer.",
        )

    return MessageVocalOut(
        **MessageOut.model_validate(message).model_dump(),
        audio_base64=base64.b64encode(audio_reponse).decode("ascii") if audio_reponse is not None else None,
    )


@router.post("/actions/{id_action}/confirmer", response_model=ActionIAOut)
def confirmer_action(
    id_action: UUID,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Exécute réellement une action proposée par JARVIS — jamais déclenché
    automatiquement, uniquement sur confirmation explicite du client."""
    try:
        return service.confirmer_action(db, client.id_client, id_action)
    except service.ActionIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action introuvable ou déjà traitée.")
    except service.ActionExpireeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le délai de confirmation de cette action est dépassé.",
        )
    except CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ce compte n'existe plus.")
    except CategorieIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cette catégorie n'existe plus.")
    except SoldeInsuffisantError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant pour cette dépense.")


@router.post("/actions/{id_action}/annuler", response_model=ActionIAOut)
def annuler_action(
    id_action: UUID,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    try:
        return service.annuler_action(db, client.id_client, id_action)
    except service.ActionIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action introuvable ou déjà traitée.")
