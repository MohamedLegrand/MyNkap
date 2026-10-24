from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class InitierRechargeRequest(BaseModel):
    id_compte: int
    montant: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    # MOBILE_MONEY (défaut) : phone_number + operator + pays sont utilisés
    # (Cash-In hrpay) ; leur absence est refusée côté service (400).
    # CARTE : les trois sont ignorés (rail carte hébergé, XAF uniquement) —
    # le client est redirigé vers la page de paiement Flocash.
    methode: Literal["MOBILE_MONEY", "CARTE"] = "MOBILE_MONEY"

    @field_validator("montant")
    @classmethod
    def _montant_entier(cls, valeur: Decimal) -> Decimal:
        # Les devises couvertes (XAF/XOF/GNF...) n'ont pas de sous-unité, et
        # le rail Mobile Money n'encaisse que des entiers (amount=int(montant)
        # côté service) : un montant à décimales facturait l'entier tronqué
        # mais créditait la valeur décimale complète (ex. facturé 1, crédité
        # 1,99). On exige donc un montant entier à l'entrée.
        if valeur != valeur.to_integral_value():
            raise ValueError("Le montant de la recharge doit être un nombre entier (pas de décimales).")
        return valeur
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
