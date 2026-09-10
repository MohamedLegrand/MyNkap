from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field


class InitierRechargeRequest(BaseModel):
    id_compte: int
    montant: Decimal = Field(..., gt=0)
    # MOBILE_MONEY (défaut) : phone_number + operator + pays sont utilisés
    # (Cash-In hrpay) ; leur absence est refusée côté service (400).
    # CARTE : les trois sont ignorés (rail carte hébergé, XAF uniquement) —
    # le client est redirigé vers la page de paiement Flocash.
    methode: Literal["MOBILE_MONEY", "CARTE"] = "MOBILE_MONEY"
    phone_number: str = ""
    operator: str = ""
    pays: str = "CM"


class RechargeCompteOut(BaseModel):
    id_recharge: int
    id_compte: int
    montant: Decimal
    devise: str
    pays: str
    methode: str
    reference_hrpay: str
    # Renseignés pour une recharge carte uniquement.
    montant_facture: Optional[Decimal] = None
    checkout_url: Optional[str] = None
    statut: str
    date_creation: datetime
    date_confirmation: Optional[datetime] = None

    class Config:
        from_attributes = True
