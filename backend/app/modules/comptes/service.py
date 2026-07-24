from decimal import Decimal
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.comptes.models import CompteFinancier, ComptePrincipal
from app.modules.comptes.schemas import CompteFinancierCreate, CompteFinancierUpdate
from app.modules.dettes.models import Dette
from app.modules.transactions.models import Transaction


def obtenir_compte_du_client(
    db: Session, id_compte: int, id_client: int, for_update: bool = False
) -> Optional[CompteFinancier]:
    """
    Récupère un compte en vérifiant qu'il appartient bien au client courant.
    Ne fait volontairement pas la distinction 404/403 : on ne révèle jamais
    l'existence d'un compte qui n'appartient pas au client.

    `for_update=True` verrouille la ligne (SELECT ... FOR UPDATE) jusqu'au
    commit — indispensable avant tout débit/crédit pour empêcher deux
    opérations concurrentes de lire le même solde de départ (race
    condition/"lost update"). Ne jamais utiliser for_update pour un simple
    affichage : ça bloquerait inutilement les autres requêtes.
    """
    query = db.query(CompteFinancier).filter(
        CompteFinancier.id_compte == id_compte, CompteFinancier.id_client == id_client
    )
    if for_update:
        query = query.with_for_update()
    return query.first()


def lister_comptes(db: Session, id_client: int, include_inactifs: bool = False) -> List[CompteFinancier]:
    query = db.query(CompteFinancier).filter(CompteFinancier.id_client == id_client)
    if not include_inactifs:
        query = query.filter(CompteFinancier.est_actif.is_(True))
    return query.order_by(CompteFinancier.date_creation.desc()).all()


def crediter_compte(compte: CompteFinancier, montant: Decimal) -> None:
    """
    Augmente le solde d'un compte. Ne doit jamais être appelé seul : doit
    toujours s'accompagner de la création d'une Transaction tracée dans le
    même appelant (voir creer_compte pour le cas DEPOT_INITIAL), et le
    compte doit avoir été récupéré avec for_update=True au préalable.
    """
    compte.solde += montant


def debiter_compte(compte: CompteFinancier, montant: Decimal) -> None:
    """Diminue le solde d'un compte. Même remarque que crediter_compte."""
    compte.solde -= montant


def creer_compte(db: Session, id_client: int, payload: CompteFinancierCreate) -> CompteFinancier:
    """
    Crée un compte financier pour le client. Si un solde initial est fourni,
    une Transaction DEPOT_INITIAL est créée dans la même transaction SQL
    que le compte, pour que l'origine du montant reste toujours traçable
    (principe du solde initial traçable, 6.4).

    Pas de verrouillage nécessaire ici : `nouveau_compte` est une ligne tout
    juste insérée dans cette même transaction, invisible des autres sessions
    tant qu'elle n'est pas commit.

    TODO(module Plan/Abonnement) : vérifier ici que le client n'a pas
    atteint la limite max_comptes de son plan avant de créer le compte
    (403 + message d'upgrade si atteinte) — actuellement non appliqué,
    décision actée avec l'utilisateur.
    """
    nouveau_compte = CompteFinancier(
        id_client=id_client,
        nom=payload.nom,
        type=payload.type,
        devise=payload.devise,
        solde=0,
        est_actif=True,
    )
    db.add(nouveau_compte)
    db.flush()  # pour obtenir id_compte avant la Transaction associée

    if payload.solde_initial > 0:
        crediter_compte(nouveau_compte, payload.solde_initial)
        depot_initial = Transaction(
            id_client=id_client,
            id_compte=nouveau_compte.id_compte,
            id_categorie=None,
            montant=payload.solde_initial,
            description="Dépôt initial à la création du compte",
            type="DEPOT_INITIAL",
        )
        db.add(depot_initial)

    db.commit()
    db.refresh(nouveau_compte)

    synchroniser_compte_principal(db, id_client)
    return nouveau_compte


def modifier_compte(db: Session, compte: CompteFinancier, payload: CompteFinancierUpdate) -> CompteFinancier:
    """Modifie le nom et/ou le type d'un compte. Le solde n'est jamais
    modifiable via cette fonction (voir CompteFinancierUpdate)."""
    donnees = payload.model_dump(exclude_unset=True)
    for champ, valeur in donnees.items():
        setattr(compte, champ, valeur)

    db.commit()
    db.refresh(compte)
    return compte


def desactiver_compte(db: Session, compte: CompteFinancier) -> CompteFinancier:
    """Désactivation logique (soft delete) — jamais de suppression réelle,
    conformément au principe d'immuabilité du cahier des charges."""
    compte.est_actif = False
    db.commit()
    db.refresh(compte)
    synchroniser_compte_principal(db, compte.id_client)
    return compte


def reactiver_compte(db: Session, compte: CompteFinancier) -> CompteFinancier:
    compte.est_actif = True
    db.commit()
    db.refresh(compte)
    synchroniser_compte_principal(db, compte.id_client)
    return compte


def reconcilier_compte(db: Session, compte: CompteFinancier) -> CompteFinancier:
    """
    Recalcule le solde depuis la somme des impacts de toutes les
    transactions du compte, plutôt que de faire confiance à la valeur
    actuellement stockée — utile après un doute sur une incohérence.
    Rendu possible par le module Transactions (chaque Transaction sait
    calculer son propre impact signé via calculer_impact()).
    """
    transactions = db.query(Transaction).filter(Transaction.id_compte == compte.id_compte).all()
    compte.solde = sum((t.calculer_impact() for t in transactions), Decimal("0"))
    db.commit()
    db.refresh(compte)
    synchroniser_compte_principal(db, compte.id_client)
    return compte


def get_or_create_compte_principal(db: Session, id_client: int) -> ComptePrincipal:
    compte_principal = db.query(ComptePrincipal).filter(ComptePrincipal.id_client == id_client).first()
    if compte_principal is not None:
        return compte_principal

    compte_principal = ComptePrincipal(id_client=id_client, solde_total=0)
    db.add(compte_principal)
    try:
        db.commit()
    except IntegrityError:
        # Deux requêtes concurrentes ont tenté de créer le ComptePrincipal
        # du même client en même temps (contrainte unique sur id_client) :
        # celle qui perd la course récupère simplement la ligne créée par
        # l'autre plutôt que d'échouer.
        db.rollback()
        compte_principal = db.query(ComptePrincipal).filter(ComptePrincipal.id_client == id_client).first()
    else:
        db.refresh(compte_principal)
    return compte_principal


def synchroniser_compte_principal(db: Session, id_client: int) -> ComptePrincipal:
    """
    Recalcule solde_total en sommant les comptes actifs du client
    (principe du compte principal agrégateur, 6.6). Le ComptePrincipal
    n'est jamais crédité/débité directement — il ne fait que refléter
    l'état des comptes financiers au moment de l'appel.
    """
    compte_principal = get_or_create_compte_principal(db, id_client)

    total = (
        db.query(func.coalesce(func.sum(CompteFinancier.solde), 0))
        .filter(CompteFinancier.id_client == id_client, CompteFinancier.est_actif.is_(True))
        .scalar()
    )
    compte_principal.solde_total = total if total is not None else Decimal("0")
    db.commit()
    db.refresh(compte_principal)
    return compte_principal


def calculer_patrimoine_net(db: Session, id_client: int) -> Decimal:
    """
    Patrimoine net = solde_total - dettes restantes + créances restantes
    (principe 6.9). Interroge directement la table Dette : le module
    Dettes complet (validations, endpoints) n'est pas encore construit,
    mais la donnée existe déjà et le calcul est correct dès maintenant.

    Les créances classées PERTE sont exclues : une fois jugées
    irrécouvrables, elles cessent de compter comme actif (voir
    Dette.get_impact_patrimoine_net).
    """
    compte_principal = synchroniser_compte_principal(db, id_client)

    dettes = db.query(Dette).filter(Dette.id_client == id_client, Dette.type == "DETTE").all()
    total_dettes = sum((d.montant_total - d.montant_rembourse for d in dettes), Decimal("0"))

    creances = (
        db.query(Dette)
        .filter(Dette.id_client == id_client, Dette.type == "CREANCE", Dette.statut != "PERTE")
        .all()
    )
    total_creances = sum((c.montant_total - c.montant_rembourse for c in creances), Decimal("0"))

    return compte_principal.solde_total - total_dettes + total_creances
