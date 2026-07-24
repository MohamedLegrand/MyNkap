from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.budgets import service
from app.modules.budgets.models import Budget
from app.modules.budgets.schemas import (
    BudgetCreate,
    BudgetOut,
    BudgetUpdate,
    CategorieCreate,
    CategorieOut,
)

router = APIRouter(tags=["Budgets"])


def _to_out(budget: Budget, valeurs: dict) -> BudgetOut:
    return BudgetOut(
        id_budget=budget.id_budget,
        id_client=budget.id_client,
        id_categorie=budget.id_categorie,
        montant_limite=budget.montant_limite,
        mois=budget.mois,
        annee=budget.annee,
        alerte_80=budget.alerte_80,
        alerte_100=budget.alerte_100,
        est_actif=budget.est_actif,
        date_creation=budget.date_creation,
        date_modification=budget.date_modification,
        montant_depense=valeurs["montant_depense"],
        montant_restant=valeurs["montant_restant"],
        pourcentage_utilise=valeurs["pourcentage_utilise"],
        est_depasse=valeurs["est_depasse"],
    )


# --- Endpoints pour les Catégories ---

@router.post("/categories", response_model=CategorieOut, status_code=status.HTTP_201_CREATED)
def create_category(
    schema: CategorieCreate,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Crée une catégorie personnalisée de dépenses ou de revenus."""
    try:
        return service.creer_categorie(db, current_client.id_client, schema)
    except service.CategorieDejaExistanteError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une catégorie avec ce nom et ce type existe déjà.",
        )


@router.get("/categories", response_model=List[CategorieOut])
def list_categories(
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Retourne l'ensemble des catégories créées par le client connecté."""
    return service.obtenir_categories(db, current_client.id_client)


# --- Endpoints pour les Budgets ---

@router.post("/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    schema: BudgetCreate,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Crée un budget de dépenses mensuel pour une catégorie donnée."""
    try:
        budget = service.creer_budget(db, current_client.id_client, schema)
    except service.CategorieIntrouvableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La catégorie spécifiée n'existe pas ou ne vous appartient pas.",
        )
    except service.CategorieTypeInvalideError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez créer un budget que sur une catégorie de type DEPENSE.",
        )
    except service.BudgetDejaExistantError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un budget existe déjà pour cette catégorie ce mois-ci.",
        )
    valeurs = service.calculer_valeurs_budget(db, budget)
    return _to_out(budget, valeurs)


@router.get("/budgets", response_model=List[BudgetOut])
def list_budgets(
    request: Request,
    include_inactifs: bool = False,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Liste des budgets du client avec calcul dynamique des dépenses. Par
    défaut, ne renvoie que les budgets actifs."""
    resultats = service.lister_budgets(db, current_client.id_client, include_inactifs, request)
    return [_to_out(budget, valeurs) for budget, valeurs in resultats]


@router.get("/budgets/{id_budget}", response_model=BudgetOut)
def get_budget(
    id_budget: int,
    request: Request,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Récupère un budget par son ID, recalcule ses consommations et
    vérifie les alertes."""
    try:
        budget, valeurs = service.obtenir_budget(db, id_budget, current_client.id_client, request)
    except service.BudgetIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget introuvable.")
    return _to_out(budget, valeurs)


@router.put("/budgets/{id_budget}", response_model=BudgetOut)
def update_budget(
    id_budget: int,
    schema: BudgetUpdate,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Modifie la limite d'un budget. Réinitialise les flags d'alerte."""
    try:
        budget, valeurs = service.modifier_budget(db, id_budget, current_client.id_client, schema)
    except service.BudgetIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget introuvable.")
    return _to_out(budget, valeurs)


@router.delete("/budgets/{id_budget}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    id_budget: int,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    """Désactivation logique — jamais de suppression réelle."""
    try:
        service.desactiver_budget(db, id_budget, current_client.id_client)
    except service.BudgetIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget introuvable.")


@router.post("/budgets/{id_budget}/reactiver", response_model=BudgetOut)
def reactivate_budget(
    id_budget: int,
    current_client: Client = Depends(get_current_active_client),
    db: Session = Depends(get_db),
):
    try:
        budget, valeurs = service.reactiver_budget(db, id_budget, current_client.id_client)
    except service.BudgetIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget introuvable.")
    return _to_out(budget, valeurs)
