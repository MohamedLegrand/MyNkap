from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    titre: Optional[str] = Field(default=None, max_length=100)


class MessageCreate(BaseModel):
    contenu: str = Field(..., min_length=1, max_length=2000)


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
    date_creation: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id_conversation: UUID
    titre: Optional[str]
    date_creation: datetime
    date_dernier_message: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: List[MessageOut]
