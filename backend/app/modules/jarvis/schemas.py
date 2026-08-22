from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    titre: Optional[str] = Field(default=None, max_length=100)


class MessageCreate(BaseModel):
    contenu: str = Field(..., min_length=1, max_length=2000)


class ActionIAOut(BaseModel):
    """Action proposée par JARVIS, en attente de confirmation explicite du
    client — voir jarvis.service.confirmer_action. `resume` est toujours un
    texte lisible construit à partir des vraies données du client, jamais
    du texte brut fourni par le fournisseur IA."""
    id_action: UUID
    type_action: str
    resume: str
    statut: str
    date_expiration: Optional[datetime]

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id_message: UUID
    type: str
    canal: str
    contenu: str
    necessite_clarification: bool
    options_suggerees: Optional[List[str]]
    peut_se_permettre: Optional[bool]
    montant_suggere: Optional[Decimal]
    conseil_supplementaire: Optional[str]
    actions: List[ActionIAOut] = []
    date_creation: datetime

    class Config:
        from_attributes = True


class MessageVocalOut(MessageOut):
    # None si la transcription/le raisonnement ont réussi mais que la
    # synthèse vocale finale a échoué (voir service.poser_question_vocale)
    # — la réponse texte reste utilisable même sans audio.
    audio_base64: Optional[str]


class ConversationOut(BaseModel):
    id_conversation: UUID
    titre: Optional[str]
    date_creation: datetime
    date_dernier_message: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: List[MessageOut]
