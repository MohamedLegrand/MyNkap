import calendar
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.budgets.models import Categorie
from app.modules.comptes import service as comptes_service
from app.modules.comptes.models import CompteFinancier
from app.modules.comptes.service import crediter_compte, debiter_compte, synchroniser_compte_principal
from app.modules.transactions.models import Transaction, TransactionRecurrente, TemplateTransaction, Transfert
from app.modules.transactions.schemas import (
    TransactionCreate,
    TransactionRecurrenteCreate,
    TransactionRecurrenteUpdate,
    TemplateTransactionCreate,
    TemplateTransactionUpdate,
    TransfertCreate,
)


class CompteIntrouvableError(Exception):
    """Le compte n'existe pas, n'appartient pas au client, ou est désactivé."""


class TransactionIntrouvableError(Exception):
    """La transaction n'existe pas ou n'appartient pas au client."""


class CategorieIntrouvableError(Exception):
    """La catégorie n'existe pas ou n'appartient pas au client."""


class SoldeInsuffisantError(Exception):
    """Le compte n'a pas les fonds nécessaires pour cette dépense/ce transfert/cette annulation."""


class TransactionDejaAnnuleeError(Exception):
    """La transaction a déjà une annulation associée, ou est elle-même une annulation."""


class TransfertInvalideError(Exception):
    """Le compte source et destination sont identiques."""


class TransactionRecurrenteIntrouvableError(Exception):
    """La récurrence n'existe pas ou n'appartient pas au client."""


class TemplateIntrouvableError(Exception):
    """Le template n'existe pas, n'appartient pas au client, ou est désactivé."""


def _obtenir_compte_actif(db: Session, id_compte: int, id_client: int, for_update: bool = False) -> CompteFinancier:
    """
    `for_update=True` doit être utilisé partout où ce compte va être
    débité/crédité dans la foulée, pour empêcher deux opérations
    concurrentes de partir du même solde de départ (voir
    comptes.service.obtenir_compte_du_client).
    """
    compte = comptes_service.obtenir_compte_du_client(db, id_compte, id_client, for_update=for_update)
    if compte is None or not compte.est_actif:
        raise CompteIntrouvableError()
    return compte


def _appliquer_impact(compte: CompteFinancier, impact: Decimal) -> None:
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
    jamais l'un sans l'autre (principe d'atomicité, 6.3). Le compte est
    verrouillé (FOR UPDATE) pour toute la durée de l'opération.
    """
    compte = _obtenir_compte_actif(db, payload.id_compte, id_client, for_update=True)

    categorie = (
        db.query(Categorie)
        .filter(Categorie.id_categorie == payload.id_categorie, Categorie.id_client == id_client)
        .first()
    )
    if categorie is None or not categorie.est_actif:
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
    (principe d'immuabilité, 6.2). Refuse l'annulation si elle ferait
    passer le solde du compte sous zéro (ex : annuler un DEPOT_INITIAL
    après avoir dépensé une partie de cet argent).
    """
    originale = obtenir_transaction_du_client(db, id_transaction, id_client)
    if originale is None:
        raise TransactionIntrouvableError()

    if originale.type == "ANNULATION":
        raise TransactionDejaAnnuleeError()

    deja_annulee = (
        db.query(Transaction)
        .filter(Transaction.id_transaction_annulee == originale.id_transaction)
        .first()
    )
    if deja_annulee is not None:
        raise TransactionDejaAnnuleeError()

    compte = comptes_service.obtenir_compte_du_client(db, originale.id_compte, id_client, for_update=True)
    if compte is None:
        raise CompteIntrouvableError()

    # Calculé à partir de l'originale, avant toute insertion : si le
    # découvert est refusé, aucune ligne ANNULATION ne doit exister, même
    # temporairement (pas de flush() à annuler après coup).
    impact = -originale.calculer_impact()
    if compte.solde + impact < 0:
        raise SoldeInsuffisantError()

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

    _appliquer_impact(compte, impact)

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
        moyenne = sum((t.montant for t in precedentes), Decimal("0")) / len(precedentes)
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

    Les deux comptes sont verrouillés (FOR UPDATE) dans un ordre constant
    basé sur id_compte (le plus petit d'abord), et non dans l'ordre
    source->destination : un virement A->B et un virement concurrent B->A
    verrouilleraient sinon les deux comptes en sens inverse l'un de
    l'autre, un cas classique de deadlock.
    """
    if payload.id_compte_source == payload.id_compte_destination:
        raise TransfertInvalideError()

    id_premier, id_second = sorted((payload.id_compte_source, payload.id_compte_destination))
    comptes_verrouilles = {
        id_premier: _obtenir_compte_actif(db, id_premier, id_client, for_update=True),
        id_second: _obtenir_compte_actif(db, id_second, id_client, for_update=True),
    }
    source = comptes_verrouilles[payload.id_compte_source]
    destination = comptes_verrouilles[payload.id_compte_destination]

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


# --- Transactions récurrentes ---

def _avancer_date(date_actuelle: date_type, frequence: str) -> date_type:
    """
    Avance à partir de la date stockée (jamais depuis "aujourd'hui") pour
    préserver l'ancrage : un loyer programmé le 5 reste programmé le 5,
    même si le job n'a tourné qu'après une panne de plusieurs jours.
    Cale sur le dernier jour du mois cible quand le jour d'origine
    n'existe pas partout (31, 30, 29 février).
    """
    if frequence == "HEBDOMADAIRE":
        return date_actuelle + timedelta(days=7)

    mois_a_ajouter = {"MENSUELLE": 1, "TRIMESTRIELLE": 3, "ANNUELLE": 12}[frequence]
    mois_total = date_actuelle.month - 1 + mois_a_ajouter
    annee = date_actuelle.year + mois_total // 12
    mois = mois_total % 12 + 1
    dernier_jour_du_mois = calendar.monthrange(annee, mois)[1]
    jour = min(date_actuelle.day, dernier_jour_du_mois)
    return date_type(annee, mois, jour)


def creer_transaction_recurrente(
    db: Session, id_client: int, payload: TransactionRecurrenteCreate
) -> TransactionRecurrente:
    compte = _obtenir_compte_actif(db, payload.id_compte, id_client)
    categorie = (
        db.query(Categorie)
        .filter(Categorie.id_categorie == payload.id_categorie, Categorie.id_client == id_client)
        .first()
    )
    if categorie is None or not categorie.est_actif:
        raise CategorieIntrouvableError()

    recurrence = TransactionRecurrente(
        id_client=id_client,
        id_compte=compte.id_compte,
        id_categorie=categorie.id_categorie,
        montant=payload.montant,
        type=payload.type,
        description=payload.description,
        frequence=payload.frequence,
        prochaine_execution=payload.prochaine_execution,
        date_fin=payload.date_fin,
    )
    db.add(recurrence)
    db.commit()
    db.refresh(recurrence)
    return recurrence


def lister_transactions_recurrentes(
    db: Session, id_client: int, include_inactifs: bool = False
) -> List[TransactionRecurrente]:
    query = db.query(TransactionRecurrente).filter(TransactionRecurrente.id_client == id_client)
    if not include_inactifs:
        query = query.filter(TransactionRecurrente.est_active.is_(True))
    return query.order_by(TransactionRecurrente.prochaine_execution.asc()).all()


def obtenir_transaction_recurrente_du_client(
    db: Session, id_transaction_recurrente: int, id_client: int
) -> Optional[TransactionRecurrente]:
    return (
        db.query(TransactionRecurrente)
        .filter(
            TransactionRecurrente.id_transaction_recurrente == id_transaction_recurrente,
            TransactionRecurrente.id_client == id_client,
        )
        .first()
    )


def modifier_transaction_recurrente(
    db: Session, id_transaction_recurrente: int, id_client: int, payload: TransactionRecurrenteUpdate
) -> TransactionRecurrente:
    recurrence = obtenir_transaction_recurrente_du_client(db, id_transaction_recurrente, id_client)
    if recurrence is None:
        raise TransactionRecurrenteIntrouvableError()

    donnees = payload.model_dump(exclude_unset=True)
    for champ, valeur in donnees.items():
        setattr(recurrence, champ, valeur)

    db.commit()
    db.refresh(recurrence)
    return recurrence


def desactiver_transaction_recurrente(db: Session, id_transaction_recurrente: int, id_client: int) -> TransactionRecurrente:
    recurrence = obtenir_transaction_recurrente_du_client(db, id_transaction_recurrente, id_client)
    if recurrence is None:
        raise TransactionRecurrenteIntrouvableError()

    recurrence.est_active = False
    db.commit()
    db.refresh(recurrence)
    return recurrence


def reactiver_transaction_recurrente(db: Session, id_transaction_recurrente: int, id_client: int) -> TransactionRecurrente:
    recurrence = obtenir_transaction_recurrente_du_client(db, id_transaction_recurrente, id_client)
    if recurrence is None:
        raise TransactionRecurrenteIntrouvableError()

    recurrence.est_active = True
    db.commit()
    db.refresh(recurrence)
    return recurrence


def _executer_une_recurrence(db: Session, id_transaction_recurrente: int) -> Optional[TransactionRecurrente]:
    """
    Traite une seule récurrence, dans sa propre unité de travail : l'échec
    (ou le succès) de l'une n'affecte jamais les autres récurrences du
    batch. Le verrou FOR UPDATE protège la ré-entrance dans le même run
    (ex. requête dupliquée) ; il ne protège pas une exécution vraiment
    concurrente entre deux process, car enregistrer_transaction() committe
    en interne et relâche donc ce verrou avant qu'on avance
    prochaine_execution. Un déploiement Celery Beat standard n'a qu'un
    seul scheduler actif à la fois, ce qui suffit ici.
    """
    recurrence = (
        db.query(TransactionRecurrente)
        .filter(TransactionRecurrente.id_transaction_recurrente == id_transaction_recurrente)
        .with_for_update()
        .first()
    )
    if recurrence is None or not recurrence.est_active or recurrence.prochaine_execution > date_type.today():
        db.commit()
        return recurrence

    payload = TransactionCreate(
        id_compte=recurrence.id_compte,
        id_categorie=recurrence.id_categorie,
        montant=recurrence.montant,
        type=recurrence.type,
        description=recurrence.description,
    )
    try:
        transaction = enregistrer_transaction(db, recurrence.id_client, payload)
    except (CompteIntrouvableError, CategorieIntrouvableError, SoldeInsuffisantError) as erreur:
        # Ne jamais avancer prochaine_execution sur un échec : le prochain
        # passage du batch (demain) retentera automatiquement, sans code
        # de relance dédié.
        db.rollback()
        enregistrer_action(
            db,
            id_utilisateur=recurrence.id_client,
            action="ECHEC_TRANSACTION_RECURRENTE",
            ressource="TransactionRecurrente",
            id_ressource=recurrence.id_transaction_recurrente,
            donnees_apres={"erreur": type(erreur).__name__},
        )
        return recurrence

    transaction.est_recurrente = True
    transaction.id_transaction_recurrente = recurrence.id_transaction_recurrente

    recurrence.prochaine_execution = _avancer_date(recurrence.prochaine_execution, recurrence.frequence)
    if recurrence.date_fin is not None and recurrence.prochaine_execution > recurrence.date_fin:
        recurrence.est_active = False

    db.commit()
    db.refresh(recurrence)
    return recurrence


def verifier_et_executer_recurrences(db: Session) -> List[TransactionRecurrente]:
    """
    Point d'entrée du batch quotidien (appelé par la tâche Celery
    verifier_transactions_recurrentes). Fonction Python normale,
    volontairement indépendante de Celery pour rester testable sans
    worker ni Redis démarrés.
    """
    aujourdhui = date_type.today()
    dues = (
        db.query(TransactionRecurrente.id_transaction_recurrente)
        .filter(TransactionRecurrente.est_active.is_(True), TransactionRecurrente.prochaine_execution <= aujourdhui)
        .all()
    )
    return [_executer_une_recurrence(db, id_recurrence) for (id_recurrence,) in dues]


# --- Templates de transaction ---

def creer_template(db: Session, id_client: int, payload: TemplateTransactionCreate) -> TemplateTransaction:
    compte = _obtenir_compte_actif(db, payload.id_compte, id_client)
    categorie = (
        db.query(Categorie)
        .filter(Categorie.id_categorie == payload.id_categorie, Categorie.id_client == id_client)
        .first()
    )
    if categorie is None or not categorie.est_actif:
        raise CategorieIntrouvableError()

    template = TemplateTransaction(
        id_client=id_client,
        id_compte=compte.id_compte,
        id_categorie=categorie.id_categorie,
        nom=payload.nom,
        montant=payload.montant,
        type=payload.type,
        description=payload.description,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def lister_templates(db: Session, id_client: int, include_inactifs: bool = False) -> List[TemplateTransaction]:
    query = db.query(TemplateTransaction).filter(TemplateTransaction.id_client == id_client)
    if not include_inactifs:
        query = query.filter(TemplateTransaction.est_actif.is_(True))
    # Les plus utilisés en premier, pour un accès rapide depuis l'app.
    return query.order_by(TemplateTransaction.nombre_utilisations.desc()).all()


def obtenir_template_du_client(db: Session, id_template: int, id_client: int) -> Optional[TemplateTransaction]:
    return (
        db.query(TemplateTransaction)
        .filter(TemplateTransaction.id_template == id_template, TemplateTransaction.id_client == id_client)
        .first()
    )


def modifier_template(
    db: Session, id_template: int, id_client: int, payload: TemplateTransactionUpdate
) -> TemplateTransaction:
    """
    Contrairement à TransactionRecurrenteUpdate, tout est modifiable : un
    template n'est qu'un préréglage de saisie, pas un enregistrement
    financier immuable.
    """
    template = obtenir_template_du_client(db, id_template, id_client)
    if template is None:
        raise TemplateIntrouvableError()

    donnees = payload.model_dump(exclude_unset=True)

    if "id_compte" in donnees:
        compte = _obtenir_compte_actif(db, donnees["id_compte"], id_client)
        donnees["id_compte"] = compte.id_compte

    if "id_categorie" in donnees:
        categorie = (
            db.query(Categorie)
            .filter(Categorie.id_categorie == donnees["id_categorie"], Categorie.id_client == id_client)
            .first()
        )
        if categorie is None or not categorie.est_actif:
            raise CategorieIntrouvableError()
        donnees["id_categorie"] = categorie.id_categorie

    for champ, valeur in donnees.items():
        setattr(template, champ, valeur)

    db.commit()
    db.refresh(template)
    return template


def desactiver_template(db: Session, id_template: int, id_client: int) -> TemplateTransaction:
    template = obtenir_template_du_client(db, id_template, id_client)
    if template is None:
        raise TemplateIntrouvableError()

    template.est_actif = False
    db.commit()
    db.refresh(template)
    return template


def reactiver_template(db: Session, id_template: int, id_client: int) -> TemplateTransaction:
    template = obtenir_template_du_client(db, id_template, id_client)
    if template is None:
        raise TemplateIntrouvableError()

    template.est_actif = True
    db.commit()
    db.refresh(template)
    return template


def rejouer_template(db: Session, id_client: int, id_template: int) -> Transaction:
    """Crée une nouvelle Transaction à partir des valeurs mémorisées par le
    template, via le module Transactions (mêmes contrôles compte/catégorie
    actifs et solde suffisant que toute autre transaction)."""
    template = obtenir_template_du_client(db, id_template, id_client)
    if template is None or not template.est_actif:
        raise TemplateIntrouvableError()

    payload = TransactionCreate(
        id_compte=template.id_compte,
        id_categorie=template.id_categorie,
        montant=template.montant,
        type=template.type,
        description=template.description,
    )
    transaction = enregistrer_transaction(db, id_client, payload)

    template.nombre_utilisations += 1
    db.commit()
    db.refresh(template)
    return transaction
