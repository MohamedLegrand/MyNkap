from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

# --- Catalogues fermés d'icônes/couleurs pour les catégories ---
# Volontairement des listes blanches (Literal) plutôt qu'un champ texte
# libre : le client ne peut envoyer qu'une valeur de cet ensemble précis,
# rejetée par Pydantic (422) sinon. Aucune valeur fournie par l'utilisateur
# n'est jamais interprétée comme du code, un chemin de fichier ou du HTML
# (pas d'import dynamique, pas de rendu brut) — seule une correspondance
# exacte avec ces slugs figés est acceptée, côté serveur ET côté frontend.
ICONES_CATEGORIE = (
    "utensils", "car", "home", "heart-pulse", "graduation-cap", "receipt",
    "gamepad-2", "shopping-bag", "more-horizontal", "wallet", "briefcase",
    "arrow-left-right", "plus-circle", "plane", "gift", "smartphone", "wifi",
    "fuel", "baby", "dog", "dumbbell", "coffee", "shirt", "tv", "book-open",
    "piggy-bank", "credit-card", "building-2", "wrench", "shield-check",
    "stethoscope", "pill", "landmark", "hand-coins", "sparkles",
)
IconeCategorie = Literal[ICONES_CATEGORIE]

COULEURS_CATEGORIE = (
    "#254E2A",  # vert forêt
    "#22C55E",  # vert
    "#F97316",  # orange
    "#EF4444",  # rouge
    "#EAB308",  # jaune
    "#3B82F6",  # bleu
    "#8B5CF6",  # violet
    "#EC4899",  # rose
    "#14B8A6",  # sarcelle
    "#06B6D4",  # cyan
    "#64748B",  # ardoise
    "#F59E0B",  # ambre
    "#84CC16",  # citron vert
    "#6366F1",  # indigo
)
CouleurCategorie = Literal[COULEURS_CATEGORIE]

# --- Schémas pour les catégories ---
class CategorieCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(DEPENSE|REVENU)$")
    icone: Optional[IconeCategorie] = None
    couleur: Optional[CouleurCategorie] = None

class CategorieUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icone: Optional[IconeCategorie] = None
    couleur: Optional[CouleurCategorie] = None

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
