from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class AnalyseFinanciereOut(BaseModel):
    # None pour une analyse "courante" (jamais persistée, recalculée en
    # direct) ; renseigné uniquement pour un snapshot de l'historique.
    id_analyse: Optional[int] = None
    type: str
    periode_debut: date
    periode_fin: date
    resultats: Optional[dict]
    score_financier: Optional[float]
    date_generation: datetime

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    id_prediction: Optional[int] = None
    type: str
    periode_debut: date
    periode_fin: date
    montant_predit: Optional[Decimal]
    niveau_confiance: Optional[float]
    recommandations: Optional[str]
    date_generation: datetime

    class Config:
        from_attributes = True
