from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

TypeDette = Literal["DETTE", "CREANCE"]


class DetteCreate(BaseModel):
    id_compte: int
    type: TypeDette
    nom: str = Field(..., min_length=1, max_length=100)
    montant_total: Decimal = Field(..., gt=0)
    personne_impliquee: Optional[str] = None
    date_echeance: Optional[date] = None


class DetteOut(BaseModel):
    id_dette: int
    id_compte: int
    nom: str
    type: str
    montant_total: Decimal
    montant_rembourse: Decimal
    montant_restant: Decimal
    personne_impliquee: Optional[str]
    date_echeance: Optional[date]
    statut: str
    jours_avant_echeance: Optional[int]
    impact_patrimoine_net: Decimal
    est_actif: bool
    date_creation: datetime
    date_modification: datetime


class RembourserRequest(BaseModel):
    montant: Decimal = Field(..., gt=0)
    id_compte: int


class EncaisserRequest(BaseModel):
    montant: Decimal = Field(..., gt=0)
    id_compte: int
