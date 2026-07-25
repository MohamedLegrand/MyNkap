from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.epargne import service
from app.modules.epargne.models import ObjectifEpargne
from app.modules.epargne.schemas import (
    AbandonnerRequest,
    AlimenterRequest,
    ObjectifEpargneCreate,
    ObjectifEpargneOut,
    RetirerRequest,
)
from app.modules.plans.dependencies import exiger_fonctionnalite

router = APIRouter(
    prefix="/epargne",
    tags=["Objectifs d'épargne"],
    dependencies=[Depends(exiger_fonctionnalite("acces_epargne"))],
)


def _to_out(objectif: ObjectifEpargne, valeurs: dict) -> ObjectifEpargneOut:
    return ObjectifEpargneOut(
        id_objectif=objectif.id_objectif,
        id_compte_epargne=objectif.id_compte_epargne,
        nom=objectif.nom,
        montant_cible=objectif.montant_cible,
        date_echeance=objectif.date_echeance,
        statut=objectif.statut,
        date_creation=objectif.date_creation,
        date_modification=objectif.date_modification,
        montant_actuel=valeurs["montant_actuel"],
        montant_restant=valeurs["montant_restant"],
        pourcentage_atteint=valeurs["pourcentage_atteint"],
        montant_mensuel_requis=valeurs["montant_mensuel_requis"],
    )


@router.post("", response_model=ObjectifEpargneOut, status_code=status.HTTP_201_CREATED)
def creer_objectif(
    payload: ObjectifEpargneCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Crée un objectif d'épargne et son compte épargne dédié (invisible
    dans /comptes, consultable uniquement ici)."""
    objectif = service.creer_objectif(db, client.id_client, payload)
    valeurs = service.calculer_valeurs_objectif(objectif)
    return _to_out(objectif, valeurs)


@router.get("", response_model=List[ObjectifEpargneOut])
def lister_objectifs(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    objectifs = service.lister_objectifs(db, client.id_client)
    return [_to_out(o, service.calculer_valeurs_objectif(o)) for o in objectifs]


@router.get("/{id_objectif}", response_model=ObjectifEpargneOut)
def obtenir_objectif(
    id_objectif: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    objectif = service.obtenir_objectif_du_client(db, id_objectif, client.id_client)
    if objectif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objectif d'épargne introuvable.")
    valeurs = service.calculer_valeurs_objectif(objectif)
    return _to_out(objectif, valeurs)


def _gerer_erreurs_operation(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except service.ObjectifIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objectif d'épargne introuvable.")
    except service.ObjectifVerrouilleError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet objectif est abandonné : plus aucune opération n'est possible.",
        )
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    except service.SoldeInsuffisantError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant sur le compte source.")
    except service.TransfertInvalideError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le compte source et destination doivent être différents.",
        )


@router.post("/{id_objectif}/alimenter", response_model=ObjectifEpargneOut)
def alimenter(
    id_objectif: int,
    payload: AlimenterRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Transfère de l'argent d'un compte du client vers le compte épargne
    dédié — jamais une dépense, neutre sur le patrimoine net."""
    objectif = _gerer_erreurs_operation(
        service.alimenter, db, client.id_client, id_objectif, payload.montant, payload.id_compte_source
    )
    valeurs = service.calculer_valeurs_objectif(objectif)
    return _to_out(objectif, valeurs)


@router.post("/{id_objectif}/retirer", response_model=ObjectifEpargneOut)
def retirer(
    id_objectif: int,
    payload: RetirerRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Transfère de l'argent du compte épargne dédié vers un compte de
    destination choisi par le client, sans abandonner l'objectif."""
    objectif = _gerer_erreurs_operation(
        service.retirer, db, client.id_client, id_objectif, payload.montant, payload.id_compte_destination
    )
    valeurs = service.calculer_valeurs_objectif(objectif)
    return _to_out(objectif, valeurs)


@router.post("/{id_objectif}/abandonner", response_model=ObjectifEpargneOut)
def abandonner(
    id_objectif: int,
    payload: AbandonnerRequest,
    request: Request,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Vide le compte épargne dédié vers un compte choisi, verrouille
    définitivement l'objectif et désactive le compte dédié."""
    objectif = _gerer_erreurs_operation(
        service.abandonner, db, client.id_client, id_objectif, payload.id_compte_destination, request=request
    )
    valeurs = service.calculer_valeurs_objectif(objectif)
    return _to_out(objectif, valeurs)
