from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

FrequenceTontine = Literal["HEBDOMADAIRE", "MENSUELLE"]


class MembreTontineCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    telephone: Optional[str] = Field(None, max_length=30)


class TontineCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    montant_cotisation: Decimal = Field(..., gt=0)
    devise: str = "XAF"
    frequence: FrequenceTontine
    date_debut: date
    # L'ordre de la liste fixe l'ordre de rotation (qui reçoit au tour 1,
    # 2, 3...). Une tontine sans au moins 2 membres n'a pas de sens.
    membres: List[MembreTontineCreate] = Field(..., min_length=2)


class CotisationVersementUpdate(BaseModel):
    est_versee: bool


class MembreTontineOut(BaseModel):
    id_membre: int
    nom: str
    telephone: Optional[str]
    ordre: int

    class Config:
        from_attributes = True


class CotisationTourOut(BaseModel):
    id_cotisation: int
    id_membre: int
    nom_membre: str
    est_versee: bool
    date_versement: Optional[datetime]


class TourTontineOut(BaseModel):
    id_tour: int
    numero: int
    id_membre_beneficiaire: int
    nom_beneficiaire: str
    date_prevue: date
    statut: str
    montant_total_attendu: Decimal
    nombre_cotisations_versees: int
    nombre_cotisations_total: int
    cotisations: List[CotisationTourOut]


class TontineOut(BaseModel):
    id_tontine: int
    nom: str
    montant_cotisation: Decimal
    devise: str
    frequence: str
    date_debut: date
    statut: str
    nombre_membres: int
    montant_total_par_tour: Decimal
    numero_tour_actuel: Optional[int]
    date_creation: datetime

    class Config:
        from_attributes = True


class TontineDetailOut(TontineOut):
    membres: List[MembreTontineOut]
    tours: List[TourTontineOut]
