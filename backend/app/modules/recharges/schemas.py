from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class InitierRechargeRequest(BaseModel):
    id_compte: int
    montant: Decimal = Field(..., gt=0)
    phone_number: str
    operator: str
    pays: str


class RechargeCompteOut(BaseModel):
    id_recharge: int
    id_compte: int
    montant: Decimal
    devise: str
    pays: str
    reference_hrpay: str
    statut: str
    date_creation: datetime
    date_confirmation: Optional[datetime] = None

    class Config:
        from_attributes = True
