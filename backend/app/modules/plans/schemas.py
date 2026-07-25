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
    nom_plan: str
    # Requis sauf pour revenir à GRATUIT (voir service.changer_plan).
    cycle_facturation: Optional[Literal["MENSUEL", "ANNUEL"]] = None
