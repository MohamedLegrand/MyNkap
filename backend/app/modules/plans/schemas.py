from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel


class PrixDeviseOut(BaseModel):
    devise: str
    prix_mensuel: Decimal
    prix_annuel: Decimal

    class Config:
        from_attributes = True


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
    # Prix dans chaque devise couverte par HR-Skills Pay (voir
    # Plan.prix_devises) — permet au frontend d'afficher le montant réel
    # avant paiement sans appel supplémentaire. prix_mensuel/prix_annuel
    # ci-dessus restent le prix de référence XAF affiché publiquement.
    prix_devises: list[PrixDeviseOut] = []

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


class DonneesVerrouilleesOut(BaseModel):
    """Compteurs uniquement (jamais les données) — voir
    service.compter_donnees_verrouillees."""
    dettes: int
    epargne: int
    tontines: int
    transactions_recurrentes: int
    templates: int
    jarvis: int


class ChangerPlanRequest(BaseModel):
    # Uniquement pour revenir à GRATUIT (aucun paiement requis) — voir
    # InitierPaiementRequest pour souscrire à un plan payant.
    nom_plan: Literal["GRATUIT"]


class InitierPaiementRequest(BaseModel):
    nom_plan: Literal["ESSENTIEL", "PREMIUM"]
    cycle_facturation: Literal["MENSUEL", "ANNUEL"]
    phone_number: str
    operator: str
    # Code pays HR-Skills Pay (ex. "CM", "SN") — détermine à la fois
    # l'opérateur valide et la devise/prix réels appliqués (voir
    # service._valider_pays_et_operateur).
    pays: str


class PaiementAbonnementOut(BaseModel):
    id_paiement: int
    plan_demande: PlanOut
    cycle_facturation: str
    montant: Decimal
    devise: str
    pays: str
    reference_hrpay: str
    statut: str
    date_creation: datetime
    date_confirmation: Optional[datetime]

    class Config:
        from_attributes = True


class OperateurPaysOut(BaseModel):
    """Un pays Mobile Money couvert par HR-Skills Pay, avec sa devise et ses
    opérateurs disponibles — voir service.obtenir_pays_disponibles."""
    pays: str
    nom: str
    devise: str
    operateurs: list[str]
