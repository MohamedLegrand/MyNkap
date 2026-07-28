from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import Request
from sqlalchemy import extract, func, cast, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.budgets.models import Budget, Categorie
from app.modules.budgets.schemas import BudgetCreate, BudgetUpdate, CategorieCreate, CategorieUpdate
from app.modules.notifications import service as notifications_service
from app.modules.transactions.models import Transaction

SEUIL_ALERTE_80 = 80.0
SEUIL_ALERTE_100 = 100.0

# Jeu de catégories usuelles, pertinentes pour le marché centrafricain visé,
# créées automatiquement à l'inscription (voir creer_categories_par_defaut)
# pour qu'un client puisse enregistrer une transaction dès sa première
# connexion sans devoir d'abord construire lui-même sa liste de catégories.
CATEGORIES_PAR_DEFAUT = [
    {"nom": "Alimentation", "type": "DEPENSE", "icone": "utensils", "couleur": "#F97316"},
    {"nom": "Transport", "type": "DEPENSE", "icone": "car", "couleur": "#3B82F6"},
    {"nom": "Logement", "type": "DEPENSE", "icone": "home", "couleur": "#8B5CF6"},
    {"nom": "Santé", "type": "DEPENSE", "icone": "heart-pulse", "couleur": "#EF4444"},
    {"nom": "Éducation", "type": "DEPENSE", "icone": "graduation-cap", "couleur": "#06B6D4"},
    {"nom": "Factures & Services", "type": "DEPENSE", "icone": "receipt", "couleur": "#64748B"},
    {"nom": "Loisirs", "type": "DEPENSE", "icone": "gamepad-2", "couleur": "#EC4899"},
    {"nom": "Achats personnels", "type": "DEPENSE", "icone": "shopping-bag", "couleur": "#14B8A6"},
    {"nom": "Autres dépenses", "type": "DEPENSE", "icone": "more-horizontal", "couleur": "#94A3B8"},
    {"nom": "Salaire", "type": "REVENU", "icone": "wallet", "couleur": "#22C55E"},
    {"nom": "Business", "type": "REVENU", "icone": "briefcase", "couleur": "#10B981"},
    {"nom": "Transferts reçus", "type": "REVENU", "icone": "arrow-left-right", "couleur": "#0EA5E9"},
    {"nom": "Autres revenus", "type": "REVENU", "icone": "plus-circle", "couleur": "#84CC16"},
]


class CategorieIntrouvableError(Exception):
    """La catégorie n'existe pas ou n'appartient pas au client."""


class CategorieDejaExistanteError(Exception):
    """Une catégorie avec ce nom et ce type existe déjà pour ce client."""


class CategorieTypeInvalideError(Exception):
    """Un budget ne peut être créé que sur une catégorie de type DEPENSE."""


class BudgetIntrouvableError(Exception):
    """Le budget n'existe pas ou n'appartient pas au client."""


class BudgetDejaExistantError(Exception):
    """Un budget existe déjà pour cette catégorie, ce mois et cette année."""


# --- Services pour les Catégories ---

def creer_categorie(db: Session, id_client: int, schema: CategorieCreate) -> Categorie:
    """
    Crée une nouvelle catégorie personnalisée pour le client. Vérifiée en
    amont pour un message d'erreur clair, ET protégée par la contrainte
    UNIQUE en base (voir modèle) qui rattrape une éventuelle course entre
    deux requêtes concurrentes.
    """
    existant = db.query(Categorie).filter(
        Categorie.id_client == id_client,
        Categorie.nom == schema.nom,
        Categorie.type == schema.type,
    ).first()
    if existant:
        raise CategorieDejaExistanteError()

    db_categorie = Categorie(
        id_client=id_client,
        nom=schema.nom,
        type=schema.type,
        icone=schema.icone,
        couleur=schema.couleur,
    )
    db.add(db_categorie)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CategorieDejaExistanteError()
    db.refresh(db_categorie)
    return db_categorie


def creer_categories_par_defaut(db: Session, id_client: int) -> List[Categorie]:
    """
    Seed d'un jeu de catégories usuelles pour le nouveau client (voir
    CATEGORIES_PAR_DEFAUT). Pas de commit ici : inséré dans la même
    transaction SQL que la création du Client et de son Profile (voir
    auth.services.creer_client), pour que le compte naisse déjà utilisable
    — sans ce seed, un client ne peut enregistrer aucune transaction
    DEPENSE/REVENU tant qu'il n'a pas d'abord créé une catégorie lui-même.
    """
    categories = [Categorie(id_client=id_client, **defaut) for defaut in CATEGORIES_PAR_DEFAUT]
    db.add_all(categories)
    return categories


def obtenir_categorie_du_client(db: Session, id_categorie: int, id_client: int) -> Optional[Categorie]:
    return (
        db.query(Categorie)
        .filter(Categorie.id_categorie == id_categorie, Categorie.id_client == id_client)
        .first()
    )


def obtenir_categories(db: Session, id_client: int, include_inactifs: bool = False) -> List[Categorie]:
    query = db.query(Categorie).filter(Categorie.id_client == id_client)
    if not include_inactifs:
        query = query.filter(Categorie.est_actif.is_(True))
    return query.all()


def modifier_categorie(db: Session, id_categorie: int, id_client: int, schema: CategorieUpdate) -> Categorie:
    """Modifie nom/icône/couleur d'une catégorie. Le type (DEPENSE/REVENU)
    n'est volontairement pas modifiable : ça changerait rétroactivement le
    sens des Transaction et Budget qui la référencent déjà."""
    categorie = obtenir_categorie_du_client(db, id_categorie, id_client)
    if categorie is None:
        raise CategorieIntrouvableError()

    donnees = schema.model_dump(exclude_unset=True)
    for champ, valeur in donnees.items():
        setattr(categorie, champ, valeur)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CategorieDejaExistanteError()
    db.refresh(categorie)
    return categorie


def desactiver_categorie(db: Session, id_categorie: int, id_client: int) -> Categorie:
    """Désactivation logique — jamais de suppression réelle (voir modèle).
    N'empêche pas la désactivation même si des Budget/Transaction actifs la
    référencent : ça bloque seulement toute NOUVELLE utilisation (voir
    creer_budget et transactions.enregistrer_transaction), l'historique
    reste valide."""
    categorie = obtenir_categorie_du_client(db, id_categorie, id_client)
    if categorie is None:
        raise CategorieIntrouvableError()

    categorie.est_actif = False
    db.commit()
    db.refresh(categorie)
    return categorie


def reactiver_categorie(db: Session, id_categorie: int, id_client: int) -> Categorie:
    categorie = obtenir_categorie_du_client(db, id_categorie, id_client)
    if categorie is None:
        raise CategorieIntrouvableError()

    categorie.est_actif = True
    try:
        db.commit()
    except IntegrityError:
        # Une catégorie active avec le même (nom, type) a été créée entre
        # temps : la contrainte unique empêche une collision silencieuse.
        db.rollback()
        raise CategorieDejaExistanteError()
    db.refresh(categorie)
    return categorie


# --- Services pour les Budgets ---

def creer_budget(db: Session, id_client: int, schema: BudgetCreate) -> Budget:
    """
    Crée un budget mensuel pour une catégorie donnée.
    Garde-fous :
    - La catégorie doit être de type DEPENSE
    - Unicité (id_client, id_categorie, mois, annee) — vérifiée en amont
      pour un message d'erreur clair, ET imposée par une contrainte UNIQUE
      en base (voir modèle) qui rattrape une éventuelle course entre deux
      requêtes concurrentes.
    """
    categorie = db.query(Categorie).filter(
        Categorie.id_categorie == schema.id_categorie,
        Categorie.id_client == id_client,
    ).first()
    if not categorie or not categorie.est_actif:
        raise CategorieIntrouvableError()

    if categorie.type != "DEPENSE":
        raise CategorieTypeInvalideError()

    budget_existant = db.query(Budget).filter(
        Budget.id_client == id_client,
        Budget.id_categorie == schema.id_categorie,
        Budget.mois == schema.mois,
        Budget.annee == schema.annee,
    ).first()
    if budget_existant:
        raise BudgetDejaExistantError()

    db_budget = Budget(
        id_client=id_client,
        id_categorie=schema.id_categorie,
        montant_limite=schema.montant_limite,
        mois=schema.mois,
        annee=schema.annee,
    )
    db.add(db_budget)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BudgetDejaExistantError()
    db.refresh(db_budget)

    return db_budget


def calculer_valeurs_budget(db: Session, budget: Budget) -> dict:
    """
    Calcule dynamiquement (sans cache) le montant dépensé, restant, le
    pourcentage utilisé et si le budget est dépassé.

    Exclut les DEPENSE qui ont depuis été annulées (Transaction de type
    ANNULATION dont id_transaction_annulee pointe vers elles) — une
    dépense corrigée par le client ne doit plus compter dans son budget,
    exactement comme elle ne compte plus dans le solde de son compte.
    """
    depenses_annulees = (
        db.query(Transaction.id_transaction_annulee)
        .filter(Transaction.type == "ANNULATION", Transaction.id_transaction_annulee.isnot(None))
    ).scalar_subquery()

    montant_depense = db.query(func.sum(Transaction.montant)).filter(
        Transaction.id_client == budget.id_client,
        Transaction.id_categorie == budget.id_categorie,
        Transaction.type == "DEPENSE",
        cast(extract("month", Transaction.date), Integer) == budget.mois,
        cast(extract("year", Transaction.date), Integer) == budget.annee,
        Transaction.id_transaction.notin_(depenses_annulees),
    ).scalar() or Decimal("0.00")

    montant_depense = Decimal(str(montant_depense))
    montant_restant = budget.montant_limite - montant_depense

    if budget.montant_limite > 0:
        pourcentage_utilise = float(montant_depense / budget.montant_limite * 100)
    else:
        pourcentage_utilise = 0.0

    est_depasse = pourcentage_utilise >= SEUIL_ALERTE_100

    return {
        "montant_depense": montant_depense,
        "montant_restant": montant_restant,
        "pourcentage_utilise": pourcentage_utilise,
        "est_depasse": est_depasse,
    }


def verifier_alertes(db: Session, budget: Budget, pourcentage_utilise: float, request: Optional[Request] = None) -> None:
    """
    Compare passivement les dépenses actuelles aux seuils d'alerte en dur
    (80% et 100%). Si un seuil est franchi pour la première fois, pose le
    flag en base, le trace dans l'AuditLog et notifie le client (voir
    notifications.service).
    """
    if budget.montant_limite <= 0:
        return

    if pourcentage_utilise >= SEUIL_ALERTE_100 and not budget.alerte_100:
        budget.alerte_100 = True
        budget.alerte_80 = True  # au cas où on saute directement de <80% à >100%
        db.commit()

        enregistrer_action(
            db,
            id_utilisateur=budget.id_client,
            action="ALERTE_BUDGET_100",
            ressource="Budget",
            id_ressource=budget.id_budget,
            donnees_avant={"alerte_100": False},
            donnees_apres={"alerte_100": True, "alerte_80": True},
            request=request,
        )
        notifications_service.creer_notification_client(
            db, budget.id_client, "BUDGET_100",
            "Budget dépassé",
            f"Vous avez dépassé votre budget \"{budget.categorie.nom}\" "
            f"({round(pourcentage_utilise)}% utilisé).",
        )
    elif pourcentage_utilise >= SEUIL_ALERTE_80 and not budget.alerte_80:
        budget.alerte_80 = True
        db.commit()

        enregistrer_action(
            db,
            id_utilisateur=budget.id_client,
            action="ALERTE_BUDGET_80",
            ressource="Budget",
            id_ressource=budget.id_budget,
            donnees_avant={"alerte_80": False},
            donnees_apres={"alerte_80": True},
            request=request,
        )
        notifications_service.creer_notification_client(
            db, budget.id_client, "BUDGET_80",
            "Budget bientôt atteint",
            f"Vous avez atteint {round(pourcentage_utilise)}% de votre budget "
            f"\"{budget.categorie.nom}\".",
        )


def _obtenir_avec_valeurs(db: Session, budget: Budget, request: Optional[Request] = None) -> Tuple[Budget, dict]:
    valeurs = calculer_valeurs_budget(db, budget)
    verifier_alertes(db, budget, valeurs["pourcentage_utilise"], request)
    return budget, valeurs


def obtenir_budget_du_client(db: Session, id_budget: int, id_client: int) -> Optional[Budget]:
    return db.query(Budget).filter(Budget.id_budget == id_budget, Budget.id_client == id_client).first()


def obtenir_budget(db: Session, id_budget: int, id_client: int, request: Optional[Request] = None) -> Tuple[Budget, dict]:
    """Récupère un budget, calcule ses valeurs et vérifie les alertes."""
    budget = obtenir_budget_du_client(db, id_budget, id_client)
    if budget is None:
        raise BudgetIntrouvableError()
    return _obtenir_avec_valeurs(db, budget, request)


def lister_budgets(
    db: Session, id_client: int, include_inactifs: bool = False, request: Optional[Request] = None
) -> List[Tuple[Budget, dict]]:
    """Liste les budgets du client, avec leurs valeurs calculées. Par défaut,
    ne renvoie que les budgets actifs (voir désactiver_budget)."""
    query = db.query(Budget).filter(Budget.id_client == id_client)
    if not include_inactifs:
        query = query.filter(Budget.est_actif.is_(True))
    budgets = query.order_by(Budget.annee.desc(), Budget.mois.desc()).all()
    return [_obtenir_avec_valeurs(db, b, request) for b in budgets]


def modifier_budget(db: Session, id_budget: int, id_client: int, schema: BudgetUpdate) -> Tuple[Budget, dict]:
    """
    Modifie la limite d'un budget. Réinitialise les flags d'alerte : sans
    ça, un client qui relève sa limite après un dépassement ne serait plus
    jamais renotifié, les flags restant bloqués à True pour toujours sous
    la nouvelle limite.
    """
    budget = obtenir_budget_du_client(db, id_budget, id_client)
    if budget is None:
        raise BudgetIntrouvableError()

    budget.montant_limite = schema.montant_limite
    budget.alerte_80 = False
    budget.alerte_100 = False
    db.commit()
    db.refresh(budget)

    return _obtenir_avec_valeurs(db, budget)


def desactiver_budget(db: Session, id_budget: int, id_client: int) -> Budget:
    """Désactivation logique — jamais de suppression réelle, même principe
    que CompteFinancier (l'AuditLog garde une référence valide)."""
    budget = obtenir_budget_du_client(db, id_budget, id_client)
    if budget is None:
        raise BudgetIntrouvableError()

    budget.est_actif = False
    db.commit()
    db.refresh(budget)
    return budget


def reactiver_budget(db: Session, id_budget: int, id_client: int) -> Tuple[Budget, dict]:
    budget = obtenir_budget_du_client(db, id_budget, id_client)
    if budget is None:
        raise BudgetIntrouvableError()

    budget.est_actif = True
    db.commit()
    db.refresh(budget)
    return _obtenir_avec_valeurs(db, budget)
