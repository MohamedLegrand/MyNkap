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
    TransactionRecurrenteCreate,
    TransactionRecurrenteOut,
    TransactionRecurrenteUpdate,
    TemplateTransactionCreate,
    TemplateTransactionOut,
    TemplateTransactionUpdate,
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


# --- Transactions récurrentes ---

def _gerer_erreurs_recurrence(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except service.TransactionRecurrenteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Récurrence introuvable")
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.CategorieIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")


@router.post("/transactions-recurrentes", response_model=TransactionRecurrenteOut, status_code=status.HTTP_201_CREATED)
def creer_transaction_recurrente(
    payload: TransactionRecurrenteCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Planifie une transaction qui s'exécutera automatiquement selon la
    fréquence donnée, sans action du client (voir tâche Celery quotidienne)."""
    return _gerer_erreurs_recurrence(service.creer_transaction_recurrente, db, client.id_client, payload)


@router.get("/transactions-recurrentes", response_model=List[TransactionRecurrenteOut])
def lister_transactions_recurrentes(
    include_inactifs: bool = False,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_transactions_recurrentes(db, client.id_client, include_inactifs)


@router.get("/transactions-recurrentes/{id_transaction_recurrente}", response_model=TransactionRecurrenteOut)
def obtenir_transaction_recurrente(
    id_transaction_recurrente: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    recurrence = service.obtenir_transaction_recurrente_du_client(db, id_transaction_recurrente, client.id_client)
    if recurrence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Récurrence introuvable")
    return recurrence


@router.put("/transactions-recurrentes/{id_transaction_recurrente}", response_model=TransactionRecurrenteOut)
def modifier_transaction_recurrente(
    id_transaction_recurrente: int,
    payload: TransactionRecurrenteUpdate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return _gerer_erreurs_recurrence(
        service.modifier_transaction_recurrente, db, id_transaction_recurrente, client.id_client, payload
    )


@router.delete("/transactions-recurrentes/{id_transaction_recurrente}", status_code=status.HTTP_204_NO_CONTENT)
def desactiver_transaction_recurrente(
    id_transaction_recurrente: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Désactivation logique — jamais de suppression réelle."""
    _gerer_erreurs_recurrence(service.desactiver_transaction_recurrente, db, id_transaction_recurrente, client.id_client)


@router.post("/transactions-recurrentes/{id_transaction_recurrente}/reactiver", response_model=TransactionRecurrenteOut)
def reactiver_transaction_recurrente(
    id_transaction_recurrente: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return _gerer_erreurs_recurrence(service.reactiver_transaction_recurrente, db, id_transaction_recurrente, client.id_client)


# --- Templates de transaction ---

def _gerer_erreurs_template(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except service.TemplateIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template introuvable")
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.CategorieIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
    except service.SoldeInsuffisantError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant sur ce compte")


@router.post("/templates", response_model=TemplateTransactionOut, status_code=status.HTTP_201_CREATED)
def creer_template(
    payload: TemplateTransactionCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Mémorise des valeurs de transaction réutilisables en un tap. Ne crée
    aucune Transaction : il faut appeler /rejouer pour ça."""
    return _gerer_erreurs_template(service.creer_template, db, client.id_client, payload)


@router.get("/templates", response_model=List[TemplateTransactionOut])
def lister_templates(
    include_inactifs: bool = False,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Triés par nombre d'utilisations décroissant : les plus utilisés en premier."""
    return service.lister_templates(db, client.id_client, include_inactifs)


@router.get("/templates/{id_template}", response_model=TemplateTransactionOut)
def obtenir_template(
    id_template: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    template = service.obtenir_template_du_client(db, id_template, client.id_client)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template introuvable")
    return template


@router.put("/templates/{id_template}", response_model=TemplateTransactionOut)
def modifier_template(
    id_template: int,
    payload: TemplateTransactionUpdate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return _gerer_erreurs_template(service.modifier_template, db, id_template, client.id_client, payload)


@router.delete("/templates/{id_template}", status_code=status.HTTP_204_NO_CONTENT)
def desactiver_template(
    id_template: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Désactivation logique — jamais de suppression réelle."""
    _gerer_erreurs_template(service.desactiver_template, db, id_template, client.id_client)


@router.post("/templates/{id_template}/reactiver", response_model=TemplateTransactionOut)
def reactiver_template(
    id_template: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return _gerer_erreurs_template(service.reactiver_template, db, id_template, client.id_client)


@router.post("/templates/{id_template}/rejouer", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def rejouer_template(
    id_template: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Crée une nouvelle Transaction à partir des valeurs mémorisées par le
    template (même débit/crédit atomique qu'une saisie manuelle)."""
    return _gerer_erreurs_template(service.rejouer_template, db, client.id_client, id_template)
