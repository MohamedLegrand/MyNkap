from datetime import datetime
from decimal import Decimal
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

TypeCompte = Literal["MOBILE_MONEY", "BANCAIRE", "ESPECES", "EPARGNE", "ABONNEMENT"]

# Seuls les logos prédéfinis du frontend (public/mobile-money/, cash, carte...)
# peuvent être fixés via l'API JSON : jamais d'URL arbitraire (un logo est
# affiché tel quel dans la page du client — une URL externe permettrait du
# suivi/pistage). Un logo importé passe uniquement par POST /comptes/{id}/logo,
# qui l'héberge lui-même.
LOGO_PREDEFINI = re.compile(r"^/(mobile-money/[a-z0-9-]+|cash|carte|momo|orange)\.(jpg|png|webp|avif|svg)$")


def _valider_logo_predefini(valeur: Optional[str]) -> Optional[str]:
    if valeur is None or valeur == "":
        return None
    if not LOGO_PREDEFINI.match(valeur):
        raise ValueError("Logo invalide : choisissez un logo prédéfini ou importez votre image.")
    return valeur


class CompteFinancierCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    type: TypeCompte
    devise: str = Field(default="XAF", min_length=3, max_length=3)
    # Génère une Transaction DEPOT_INITIAL si > 0 (principe du solde initial
    # traçable, 6.4) — jamais écrit directement sans origine.
    solde_initial: Decimal = Field(default=Decimal("0"), ge=0)
    # Logo prédéfini choisi à la création (facultatif) ; pour importer sa
    # propre image, voir POST /comptes/{id}/logo.
    logo: Optional[str] = None

    _valider_logo = field_validator("logo")(_valider_logo_predefini)


class CompteFinancierUpdate(BaseModel):
    """Le solde n'est volontairement pas modifiable ici : seuls nom et type
    peuvent être corrigés après création (principe d'immuabilité, 6.3)."""
    nom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: Optional[TypeCompte] = None
    # None explicite = retirer le logo ; champ absent = inchangé.
    logo: Optional[str] = None

    _valider_logo = field_validator("logo")(_valider_logo_predefini)


class CompteFinancierOut(BaseModel):
    id_compte: int
    nom: str
    type: str
    solde: Decimal
    devise: str
    logo: Optional[str] = None
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
