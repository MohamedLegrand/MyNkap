from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.recharges import service
from app.modules.recharges.schemas import InitierRechargeRequest, RechargeCompteOut

router = APIRouter(prefix="/recharges", tags=["Recharges de compte"])


@router.post("", response_model=RechargeCompteOut, status_code=status.HTTP_201_CREATED)
def initier_recharge(
    payload: InitierRechargeRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """
    Démarre une recharge Mobile Money réelle (HR-Skills Pay) créditant un
    compte financier du client. Renvoie un statut PENDING — le compte n'est
    crédité qu'une fois la recharge confirmée par la tâche planifiée
    (polling, toutes les ~20s). Interroger GET /recharges/{id} pour suivre
    l'évolution.
    """
    try:
        return service.initier_recharge(
            db, client.id_client, payload.id_compte, payload.montant,
            payload.phone_number, payload.operator, payload.pays,
        )
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    except service.TelephoneOperateurRequisError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Numéro de téléphone et opérateur Mobile Money requis.",
        )
    except service.PaysOuOperateurInvalideError as erreur:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erreur))
    except service.PaiementRefuseError as erreur:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erreur))
    except service.ServicePaiementIndisponibleError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le service de paiement est momentanément indisponible, veuillez réessayer.",
        )


@router.get("", response_model=List[RechargeCompteOut])
def lister_mes_recharges(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_recharges_du_client(db, client.id_client)


@router.get("/{id_recharge}", response_model=RechargeCompteOut)
def obtenir_recharge(
    id_recharge: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    recharge = service.obtenir_recharge_du_client(db, id_recharge, client.id_client)
    if recharge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recharge introuvable.")
    return recharge
