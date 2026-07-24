from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ObjectifEpargneCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    montant_cible: Decimal = Field(..., gt=0)
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
    montant: Decimal = Field(..., gt=0)
    id_compte_source: int


class RetirerRequest(BaseModel):
    montant: Decimal = Field(..., gt=0)
    id_compte_destination: int


class AbandonnerRequest(BaseModel):
    # Toujours requis explicitement : pas de destination automatique
    # implicite vers un "compte principal" qui n'existe pas réellement
    # comme compte transférable (voir principe du module).
    id_compte_destination: int
