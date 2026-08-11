from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel


class PlanOut(BaseModel):
    id_plan: int
    nom: str
    prix_mensuel: Decimal
    prix_annuel: Decimal
    devise: str
    acces_dettes: bool
    acces_epargne: bool
    acces_recurrentes: bool
    acces_templates: bool
    acces_analyse: bool
    acces_jarvis: bool
    acces_rapport: bool
    acces_tontine: bool

    class Config:
        from_attributes = True


class AbonnementOut(BaseModel):
    id_abonnement: int
    plan: PlanOut
    statut: str
    date_debut: datetime
    date_fin: Optional[datetime]
    cycle_facturation: Optional[str]
    renouvellement_auto: bool

    class Config:
        from_attributes = True


class ChangerPlanRequest(BaseModel):
    # Uniquement pour revenir à GRATUIT (aucun paiement requis) — voir
    # InitierPaiementRequest pour souscrire à un plan payant.
    nom_plan: Literal["GRATUIT"]


class InitierPaiementRequest(BaseModel):
    nom_plan: Literal["ESSENTIEL", "PREMIUM"]
    cycle_facturation: Literal["MENSUEL", "ANNUEL"]
    phone_number: str
    operator: str


class PaiementAbonnementOut(BaseModel):
    id_paiement: int
    plan_demande: PlanOut
    cycle_facturation: str
    montant: Decimal
    devise: str
    reference_hrpay: str
    statut: str
    date_creation: datetime
    date_confirmation: Optional[datetime]

    class Config:
        from_attributes = True
