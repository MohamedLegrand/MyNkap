from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel

TypeRapport = Literal[
    "RELEVE_TRANSACTIONS", "BILAN_BUDGETAIRE", "DETTES_EPARGNE", "BILAN_FINANCIER", "PREDICTIONS"
]


class DemanderRapportRequest(BaseModel):
    type: TypeRapport
    periode_debut: date
    periode_fin: date


class RapportOut(BaseModel):
    id_rapport: int
    type: str
    periode_debut: date
    periode_fin: date
    statut: str
    taille: Optional[int]
    date_generation: datetime

    class Config:
        from_attributes = True
