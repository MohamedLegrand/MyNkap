from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

TypeCompte = Literal["MOBILE_MONEY", "BANCAIRE", "ESPECES", "EPARGNE"]


class CompteFinancierCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    type: TypeCompte
    devise: str = Field(default="XAF", min_length=3, max_length=3)
    # Génère une Transaction DEPOT_INITIAL si > 0 (principe du solde initial
    # traçable, 6.4) — jamais écrit directement sans origine.
    solde_initial: Decimal = Field(default=Decimal("0"), ge=0)


class CompteFinancierUpdate(BaseModel):
    """Le solde n'est volontairement pas modifiable ici : seuls nom et type
    peuvent être corrigés après création (principe d'immuabilité, 6.3)."""
    nom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: Optional[TypeCompte] = None


class CompteFinancierOut(BaseModel):
    id_compte: int
    nom: str
    type: str
    solde: Decimal
    devise: str
    est_actif: bool
    date_creation: datetime
    date_modification: datetime

    class Config:
        from_attributes = True


class ComptePrincipalOut(BaseModel):
    id_compte_principal: int
    solde_total: Decimal
    devise: str
    patrimoine_net: Decimal
    date_mise_a_jour: datetime

    class Config:
        from_attributes = True
