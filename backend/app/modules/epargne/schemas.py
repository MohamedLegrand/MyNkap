from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class SimulationObjectifRequest(BaseModel):
    montant_cible: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    date_echeance: Optional[date] = None
    # Montant déjà disponible au départ (facultatif) : réduit l'effort
    # mensuel restant à fournir.
    montant_initial: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class PointProjectionEpargne(BaseModel):
    mois: str  # "AAAA-MM"
    montant_cumule: Decimal


class SimulationObjectifOut(BaseModel):
    montant_cible: Decimal
    montant_initial: Decimal
    date_echeance: Optional[date]
    nombre_mois: Optional[int]
    montant_mensuel_requis: Optional[Decimal]
    projection: List[PointProjectionEpargne]


class ObjectifEpargneCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    montant_cible: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    date_echeance: Optional[date] = None


class ObjectifEpargneOut(BaseModel):
    id_objectif: int
    id_compte_epargne: int
    nom: str
    montant_cible: Decimal
    date_echeance: Optional[date]
    statut: str
    date_creation: datetime
    date_modification: datetime

    # Champs calculés (jamais stockés, toujours recalculés à la lecture) :
    # montant_actuel est un simple alias sur compte_epargne.solde.
    montant_actuel: Decimal
    montant_restant: Decimal
    pourcentage_atteint: float
    montant_mensuel_requis: Optional[Decimal]


class AlimenterRequest(BaseModel):
    montant: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    id_compte_source: int


class RetirerRequest(BaseModel):
    montant: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    id_compte_destination: int
    # Verrou virtuel : passer à True pour confirmer un retrait AVANT l'échéance
    # sur un objectif non atteint (sinon le retrait est refusé avec un
    # avertissement — voir service.retirer).
    confirmer_retrait_anticipe: bool = False


class AbandonnerRequest(BaseModel):
    # Toujours requis explicitement : pas de destination automatique
    # implicite vers un "compte principal" qui n'existe pas réellement
    # comme compte transférable (voir principe du module).
    id_compte_destination: int
