from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.plans import service
from app.modules.plans.schemas import AbonnementOut, ChangerPlanRequest, PlanOut

router = APIRouter(tags=["Plans & Abonnement"])


@router.get("/plans", response_model=List[PlanOut])
def lister_plans(db: Session = Depends(get_db)):
    """Catalogue public des plans tarifaires — consultable avant inscription."""
    return service.lister_plans(db)


@router.get("/abonnement", response_model=AbonnementOut)
def obtenir_mon_abonnement(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.obtenir_abonnement_actif(db, client.id_client)


@router.post("/abonnement/changer-plan", response_model=AbonnementOut)
def changer_plan(
    payload: ChangerPlanRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """
    Changement de plan simulé — aucun paiement réel n'est encore prélevé
    (fournisseur Mobile Money pas encore intégré).
    """
    try:
        return service.changer_plan(db, client.id_client, payload.nom_plan, payload.cycle_facturation)
    except service.PlanIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan introuvable.")
    except service.CycleFacturationRequisError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un cycle de facturation (MENSUEL ou ANNUEL) est requis pour ce plan.",
        )


@router.post("/abonnement/annuler-renouvellement", response_model=AbonnementOut)
def annuler_renouvellement(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Arrête le renouvellement futur — l'accès reste actif jusqu'à la fin
    de la période déjà payée (simulée)."""
    return service.annuler_renouvellement(db, client.id_client)
