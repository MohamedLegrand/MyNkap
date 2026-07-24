from datetime import date as date_type, timedelta
from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.budgets.models import Categorie
from app.modules.comptes import service as comptes_service
from app.modules.comptes.models import CompteFinancier
from app.modules.comptes.service import crediter_compte, debiter_compte, synchroniser_compte_principal
from app.modules.transactions.models import Transaction, Transfert
from app.modules.transactions.schemas import TransactionCreate, TransfertCreate


class CompteIntrouvableError(Exception):
    """Le compte n'existe pas, n'appartient pas au client, ou est désactivé."""


class CategorieIntrouvableError(Exception):
    """La catégorie n'existe pas ou n'appartient pas au client."""


class SoldeInsuffisantError(Exception):
    """Le compte n'a pas les fonds nécessaires pour cette dépense/ce transfert."""


class TransactionDejaAnnuleeError(Exception):
    """La transaction a déjà une annulation associée, ou est elle-même une annulation."""


class TransfertInvalideError(Exception):
    """Le compte source et destination sont identiques."""


def _obtenir_compte_actif(db: Session, id_compte: int, id_client: int) -> CompteFinancier:
    compte = comptes_service.obtenir_compte_du_client(db, id_compte, id_client)
    if compte is None or not compte.est_actif:
        raise CompteIntrouvableError()
    return compte


def _appliquer_impact(compte: CompteFinancier, impact: float) -> None:
    if impact >= 0:
        crediter_compte(compte, impact)
    else:
        debiter_compte(compte, -impact)


# --- Transactions ---

def lister_transactions(db: Session, id_client: int, id_compte: Optional[int] = None) -> List[Transaction]:
    query = db.query(Transaction).filter(Transaction.id_client == id_client)
    if id_compte is not None:
        query = query.filter(Transaction.id_compte == id_compte)
    return query.order_by(Transaction.date.desc(), Transaction.date_creation.desc()).all()


def obtenir_transaction_du_client(db: Session, id_transaction: int, id_client: int) -> Optional[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.id_transaction == id_transaction, Transaction.id_client == id_client)
        .first()
    )


def enregistrer_transaction(db: Session, id_client: int, payload: TransactionCreate) -> Transaction:
    """
    Enregistre une dépense ou un revenu. Le compte est débité/crédité dans
    la même transaction SQL que l'insertion de la ligne Transaction —
    jamais l'un sans l'autre (principe d'atomicité, 6.3).
    """
    compte = _obtenir_compte_actif(db, payload.id_compte, id_client)

    categorie = (
        db.query(Categorie)
        .filter(Categorie.id_categorie == payload.id_categorie, Categorie.id_client == id_client)
        .first()
    )
    if categorie is None:
        raise CategorieIntrouvableError()

    if payload.type == "DEPENSE" and not compte.est_suffisant(payload.montant):
        raise SoldeInsuffisantError()

    transaction = Transaction(
        id_client=id_client,
        id_compte=compte.id_compte,
        id_categorie=categorie.id_categorie,
        montant=payload.montant,
        type=payload.type,
        description=payload.description,
        date=payload.date or date_type.today(),
    )
    db.add(transaction)
    db.flush()

    _appliquer_impact(compte, transaction.calculer_impact())

    db.commit()
    db.refresh(transaction)

    synchroniser_compte_principal(db, id_client)
    detecter_transaction_suspecte(db, transaction)
    db.refresh(transaction)
    return transaction


def annuler_transaction(db: Session, id_client: int, id_transaction: int) -> Transaction:
    """
    Annule une transaction en créant une nouvelle transaction inverse de
    type ANNULATION — l'originale n'est jamais modifiée ni supprimée
    (principe d'immuabilité, 6.2).
    """
    originale = obtenir_transaction_du_client(db, id_transaction, id_client)
    if originale is None:
        raise CompteIntrouvableError()  # réutilisé : traité comme "ressource introuvable"

    if originale.type == "ANNULATION":
        raise TransactionDejaAnnuleeError()

    deja_annulee = (
        db.query(Transaction)
        .filter(Transaction.id_transaction_annulee == originale.id_transaction)
        .first()
    )
    if deja_annulee is not None:
        raise TransactionDejaAnnuleeError()

    compte = db.query(CompteFinancier).filter(CompteFinancier.id_compte == originale.id_compte).first()

    annulation = Transaction(
        id_client=id_client,
        id_compte=originale.id_compte,
        id_categorie=originale.id_categorie,
        montant=originale.montant,
        type="ANNULATION",
        description=f"Annulation de la transaction #{originale.id_transaction}",
        date=date_type.today(),
        id_transaction_annulee=originale.id_transaction,
    )
    db.add(annulation)
    db.flush()

    _appliquer_impact(compte, annulation.calculer_impact())

    db.commit()
    db.refresh(annulation)

    synchroniser_compte_principal(db, id_client)
    return annulation


# --- Détection de transactions suspectes (règles simples, remplaçables par
# JARVIS plus tard sans changer le modèle ni l'API) ---

SEUIL_MONTANT_INHABITUEL = 3
NB_MIN_HISTORIQUE_POUR_MOYENNE = 3
FENETRE_HISTORIQUE_JOURS = 30


def detecter_transaction_suspecte(db: Session, transaction: Transaction) -> Transaction:
    """
    Signale automatiquement une transaction comme suspecte si :
    - son montant dépasse 3x la moyenne des transactions de même type et
      catégorie sur les 30 derniers jours (à partir de 3 précédentes, pour
      éviter de flaguer la toute première transaction d'une catégorie) ;
    - ou un doublon apparent existe (même compte, montant, type, jour).
    Les écritures système (DEPOT_INITIAL, ANNULATION, ...) ne sont jamais
    évaluées : seules DEPENSE/REVENU le sont.
    """
    if transaction.type not in ("DEPENSE", "REVENU"):
        return transaction

    il_y_a_30_jours = transaction.date - timedelta(days=FENETRE_HISTORIQUE_JOURS)
    precedentes = (
        db.query(Transaction)
        .filter(
            Transaction.id_categorie == transaction.id_categorie,
            Transaction.type == transaction.type,
            Transaction.id_transaction != transaction.id_transaction,
            Transaction.date >= il_y_a_30_jours,
            Transaction.date <= transaction.date,
        )
        .all()
    )
    if len(precedentes) >= NB_MIN_HISTORIQUE_POUR_MOYENNE:
        moyenne = sum(t.montant for t in precedentes) / len(precedentes)
        if moyenne > 0 and transaction.montant > SEUIL_MONTANT_INHABITUEL * moyenne:
            return marquer_comme_suspecte(db, transaction)

    doublons = (
        db.query(Transaction)
        .filter(
            Transaction.id_compte == transaction.id_compte,
            Transaction.montant == transaction.montant,
            Transaction.type == transaction.type,
            Transaction.date == transaction.date,
            Transaction.id_transaction != transaction.id_transaction,
        )
        .count()
    )
    if doublons > 0:
        return marquer_comme_suspecte(db, transaction)

    return transaction


def marquer_comme_suspecte(db: Session, transaction: Transaction) -> Transaction:
    transaction.est_suspecte = True
    db.commit()
    db.refresh(transaction)
    return transaction


def confirmer_suspicion(db: Session, transaction: Transaction, request: Optional[Request] = None) -> Transaction:
    """
    Le client confirme que la transaction signalée est bien une erreur.
    Le flag reste actif ici : c'est un constat, pas une correction — au
    client d'appeler ensuite annuler_transaction() s'il veut corriger.
    """
    enregistrer_action(
        db,
        id_utilisateur=transaction.id_client,
        action="CONFIRMER_SUSPICION",
        ressource="Transaction",
        id_ressource=transaction.id_transaction,
        request=request,
    )
    return transaction


def annuler_suspicion(db: Session, transaction: Transaction, request: Optional[Request] = None) -> Transaction:
    """
    Le client confirme que la transaction est légitime : le flag retombe,
    mais la levée de doute est tracée dans l'AuditLog (décision actée avec
    l'utilisateur) plutôt que d'ajouter des colonnes d'historique au modèle.
    """
    transaction.est_suspecte = False
    db.commit()
    db.refresh(transaction)

    enregistrer_action(
        db,
        id_utilisateur=transaction.id_client,
        action="LEVEE_SUSPICION",
        ressource="Transaction",
        id_ressource=transaction.id_transaction,
        donnees_avant={"est_suspecte": True},
        donnees_apres={"est_suspecte": False},
        request=request,
    )
    return transaction


# --- Transferts ---

def lister_transferts(db: Session, id_client: int) -> List[Transfert]:
    return (
        db.query(Transfert)
        .filter(Transfert.id_client == id_client)
        .order_by(Transfert.date.desc(), Transfert.date_creation.desc())
        .all()
    )


def obtenir_transfert_du_client(db: Session, id_transfert: int, id_client: int) -> Optional[Transfert]:
    return (
        db.query(Transfert)
        .filter(Transfert.id_transfert == id_transfert, Transfert.id_client == id_client)
        .first()
    )


def executer_transfert(db: Session, id_client: int, payload: TransfertCreate) -> Transfert:
    """
    Débite la source et crédite la destination dans la même transaction
    SQL : soit les deux opérations réussissent, soit aucune n'est appliquée
    (rollback automatique en cas d'erreur avant le commit).
    """
    if payload.id_compte_source == payload.id_compte_destination:
        raise TransfertInvalideError()

    source = _obtenir_compte_actif(db, payload.id_compte_source, id_client)
    destination = _obtenir_compte_actif(db, payload.id_compte_destination, id_client)

    if not source.est_suffisant(payload.montant):
        raise SoldeInsuffisantError()

    transfert = Transfert(
        id_client=id_client,
        id_compte_source=source.id_compte,
        id_compte_destination=destination.id_compte,
        montant=payload.montant,
        description=payload.description,
    )
    db.add(transfert)

    debiter_compte(source, payload.montant)
    crediter_compte(destination, payload.montant)

    db.commit()
    db.refresh(transfert)

    # Neutre sur solde_total (principe 6.5), mais on resynchronise par
    # cohérence (date_mise_a_jour, et futur usage avec des dettes/créances).
    synchroniser_compte_principal(db, id_client)
    return transfert
