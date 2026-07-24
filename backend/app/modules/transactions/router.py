from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.transactions import service
from app.modules.transactions.schemas import (
    TransactionCreate,
    TransactionOut,
    TransfertCreate,
    TransfertOut,
)

router = APIRouter(tags=["Transactions & Transferts"])


def _get_transaction_ou_404(db: Session, id_transaction: int, id_client: int):
    transaction = service.obtenir_transaction_du_client(db, id_transaction, id_client)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")
    return transaction


@router.post("/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def creer_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Enregistre une dépense ou un revenu. Le compte est débité/crédité de
    façon atomique dans la même opération."""
    try:
        return service.enregistrer_transaction(db, client.id_client, payload)
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.CategorieIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
    except service.SoldeInsuffisantError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant sur ce compte")


@router.get("/transactions", response_model=List[TransactionOut])
def lister_transactions(
    id_compte: Optional[int] = None,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_transactions(db, client.id_client, id_compte)


@router.get("/transactions/{id_transaction}", response_model=TransactionOut)
def obtenir_transaction(
    id_transaction: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return _get_transaction_ou_404(db, id_transaction, client.id_client)


@router.post("/transactions/{id_transaction}/annuler", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def annuler_transaction(
    id_transaction: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Crée une transaction d'annulation inverse. L'originale n'est jamais
    modifiée ni supprimée (principe d'immuabilité)."""
    try:
        return service.annuler_transaction(db, client.id_client, id_transaction)
    except service.TransactionIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction introuvable")
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.TransactionDejaAnnuleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette transaction est déjà annulée, ou est elle-même une annulation",
        )
    except service.SoldeInsuffisantError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette annulation ferait passer le solde du compte sous zéro",
        )


@router.post("/transactions/{id_transaction}/confirmer-suspicion", response_model=TransactionOut)
def confirmer_suspicion(
    id_transaction: int,
    request: Request,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Le client confirme que la transaction signalée est bien une erreur
    (à corriger ensuite via /annuler si besoin)."""
    transaction = _get_transaction_ou_404(db, id_transaction, client.id_client)
    return service.confirmer_suspicion(db, transaction, request=request)


@router.post("/transactions/{id_transaction}/annuler-suspicion", response_model=TransactionOut)
def annuler_suspicion(
    id_transaction: int,
    request: Request,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Le client confirme que la transaction est légitime : le flag retombe,
    la levée de doute est tracée dans l'AuditLog."""
    transaction = _get_transaction_ou_404(db, id_transaction, client.id_client)
    return service.annuler_suspicion(db, transaction, request=request)


@router.post("/transferts", response_model=TransfertOut, status_code=status.HTTP_201_CREATED)
def creer_transfert(
    payload: TransfertCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Mouvement atomique entre deux comptes du même client. Neutre sur le
    patrimoine net."""
    try:
        return service.executer_transfert(db, client.id_client, payload)
    except service.TransfertInvalideError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le compte source et le compte destination doivent être différents",
        )
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.SoldeInsuffisantError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant sur le compte source")


@router.get("/transferts", response_model=List[TransfertOut])
def lister_transferts(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_transferts(db, client.id_client)


@router.get("/transferts/{id_transfert}", response_model=TransfertOut)
def obtenir_transfert(
    id_transfert: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    transfert = service.obtenir_transfert_du_client(db, id_transfert, client.id_client)
    if transfert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfert introuvable")
    return transfert
