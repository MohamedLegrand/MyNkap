from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.analyse import service
from app.modules.analyse.schemas import AnalyseFinanciereOut, PredictionOut

router = APIRouter(prefix="/analyse", tags=["Analyse & Prédictions"])


# --- Prédictions (routes littérales enregistrées avant le {type_analyse}
# générique, sinon FastAPI matcherait "predictions" comme un type d'analyse) ---

@router.get("/predictions/{type_prediction}", response_model=PredictionOut)
def obtenir_prediction(
    type_prediction: str,
    periode_debut: Optional[date] = None,
    periode_fin: Optional[date] = None,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Prédiction recalculée en direct — jamais persistée. Par défaut,
    porte sur le mois prochain (sauf RISQUE_BUDGETAIRE : le mois en cours)."""
    try:
        donnees = service.obtenir_prediction_courante(db, client.id_client, type_prediction, periode_debut, periode_fin)
    except service.TypePredictionInvalideError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type de prédiction invalide.")
    return PredictionOut(**donnees)


@router.get("/predictions/{type_prediction}/historique", response_model=List[PredictionOut])
def lister_historique_predictions(
    type_prediction: str,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Snapshots mensuels figés (voir la tâche Celery du 1er de chaque mois)."""
    try:
        return service.lister_historique_predictions(db, client.id_client, type_prediction)
    except service.TypePredictionInvalideError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type de prédiction invalide.")


# --- Analyse ---

@router.get("/{type_analyse}", response_model=AnalyseFinanciereOut)
def obtenir_analyse(
    type_analyse: str,
    periode_debut: Optional[date] = None,
    periode_fin: Optional[date] = None,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Analyse recalculée en direct sur les données réelles — jamais
    persistée. Par défaut, porte sur le mois en cours."""
    try:
        donnees = service.obtenir_analyse_courante(db, client.id_client, type_analyse, periode_debut, periode_fin)
    except service.TypeAnalyseInvalideError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'analyse invalide.")
    return AnalyseFinanciereOut(**donnees)


@router.get("/{type_analyse}/historique", response_model=List[AnalyseFinanciereOut])
def lister_historique_analyses(
    type_analyse: str,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Snapshots mensuels figés (voir la tâche Celery du 1er de chaque mois)."""
    try:
        return service.lister_historique_analyses(db, client.id_client, type_analyse)
    except service.TypeAnalyseInvalideError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'analyse invalide.")
