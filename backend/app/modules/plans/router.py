from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.plans import service
from app.modules.plans.schemas import (
    AbonnementOut,
    ChangerPlanRequest,
    InitierPaiementRequest,
    PaiementAbonnementOut,
    PlanOut,
)

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
    Retour immédiat au plan GRATUIT — aucun paiement requis. Pour
    souscrire à un plan payant, voir POST /abonnement/paiements : ça
    nécessite une confirmation Mobile Money réelle, jamais un changement
    instantané.
    """
    return service.changer_plan(db, client.id_client, payload.nom_plan)


@router.post("/abonnement/paiements", response_model=PaiementAbonnementOut, status_code=status.HTTP_201_CREATED)
def initier_paiement(
    payload: InitierPaiementRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """
    Démarre un paiement Mobile Money réel (HR-Skills Pay) pour souscrire à
    un plan payant. Renvoie un statut PENDING — le plan n'est changé
    qu'une fois le paiement confirmé par la tâche planifiée (polling,
    toutes les ~20s). Interroger GET /abonnement/paiements/{id} pour
    suivre l'évolution.
    """
    try:
        return service.initier_paiement_plan(
            db, client.id_client, payload.nom_plan, payload.cycle_facturation, payload.phone_number, payload.operator
        )
    except service.PlanIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan introuvable.")
    except service.CycleFacturationRequisError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un cycle de facturation (MENSUEL ou ANNUEL) est requis pour ce plan.",
        )
    except service.TelephoneOperateurRequisError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numéro de téléphone et opérateur Mobile Money requis.",
        )
    except service.PaiementRefuseError as erreur:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erreur))
    except service.ServicePaiementIndisponibleError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le service de paiement est momentanément indisponible, veuillez réessayer.",
        )


@router.get("/abonnement/paiements/{id_paiement}", response_model=PaiementAbonnementOut)
def obtenir_paiement(
    id_paiement: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    paiement = service.obtenir_paiement_du_client(db, id_paiement, client.id_client)
    if paiement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable.")
    return paiement


@router.post("/abonnement/annuler-renouvellement", response_model=AbonnementOut)
def annuler_renouvellement(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Arrête le renouvellement futur — l'accès reste actif jusqu'à la fin
    de la période déjà payée."""
    return service.annuler_renouvellement(db, client.id_client)
