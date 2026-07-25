from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

# --- Schémas pour les catégories ---
class CategorieCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(DEPENSE|REVENU)$")
    icone: Optional[str] = None
    couleur: Optional[str] = None

class CategorieUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icone: Optional[str] = None
    couleur: Optional[str] = None

class CategorieOut(BaseModel):
    id_categorie: int
    id_client: int
    nom: str
    type: str
    icone: Optional[str] = None
    couleur: Optional[str] = None
    est_actif: bool
    date_creation: datetime

    class Config:
        from_attributes = True

# --- Schémas pour les budgets ---
class BudgetCreate(BaseModel):
    id_categorie: int
    montant_limite: Decimal = Field(..., gt=0)
    mois: int = Field(..., ge=1, le=12)
    annee: int = Field(..., ge=2000, le=2100)

class BudgetOut(BaseModel):
    id_budget: int
    id_client: int
    id_categorie: int
    montant_limite: Decimal
    mois: int
    annee: int
    alerte_80: bool
    alerte_100: bool
    est_actif: bool
    date_creation: datetime
    date_modification: datetime

    # Champs calculés (jamais stockés, toujours recalculés à la lecture)
    montant_depense: Decimal
    montant_restant: Decimal
    pourcentage_utilise: float
    est_depasse: bool

class BudgetUpdate(BaseModel):
    montant_limite: Decimal = Field(..., gt=0)
