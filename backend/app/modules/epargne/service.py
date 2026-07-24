from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.comptes import service as comptes_service
from app.modules.comptes.models import CompteFinancier
from app.modules.epargne.models import ObjectifEpargne
from app.modules.epargne.schemas import ObjectifEpargneCreate
from app.modules.transactions import service as transactions_service
from app.modules.transactions.schemas import TransfertCreate


class ObjectifIntrouvableError(Exception):
    """L'objectif n'existe pas ou n'appartient pas au client."""


class ObjectifVerrouilleError(Exception):
    """L'objectif est ABANDONNE : plus aucune opération n'est possible."""


class CompteIntrouvableError(Exception):
    """Le compte n'existe pas, n'appartient pas au client, ou est désactivé."""


class SoldeInsuffisantError(Exception):
    """Le compte source n'a pas les fonds nécessaires pour ce transfert."""


class TransfertInvalideError(Exception):
    """Le compte source et destination sont identiques."""


def _executer_transfert(
    db: Session, id_client: int, id_compte_source: int, id_compte_destination: int, montant: Decimal, description: str
):
    """
    Traduit les exceptions du module Transactions en exceptions locales à
    Épargne — chaque module ne connaît que son propre vocabulaire
    d'exceptions (voir Comptes, Transactions, Dettes, Budgets).
    """
    payload = TransfertCreate(
        id_compte_source=id_compte_source,
        id_compte_destination=id_compte_destination,
        montant=montant,
        description=description,
    )
    try:
        return transactions_service.executer_transfert(db, id_client, payload)
    except transactions_service.TransfertInvalideError:
        raise TransfertInvalideError()
    except transactions_service.CompteIntrouvableError:
        raise CompteIntrouvableError()
    except transactions_service.SoldeInsuffisantError:
        raise SoldeInsuffisantError()


def _mois_restants(date_echeance: date) -> int:
    """Nombre de mois jusqu'à l'échéance, jamais inférieur à 1 (une échéance
    ce mois-ci ou déjà dépassée est traitée comme "il faut le montant
    maintenant", pas comme une division par zéro/négative)."""
    aujourdhui = date.today()
    mois = (date_echeance.year - aujourdhui.year) * 12 + (date_echeance.month - aujourdhui.month)
    return max(mois, 1)


def calculer_valeurs_objectif(objectif: ObjectifEpargne) -> dict:
    """
    montant_actuel est un simple alias sur le solde du compte épargne dédié
    — aucun calcul propre à faire, contrairement à Budget ou Dette.
    """
    montant_actuel = objectif.compte_epargne.solde
    montant_restant = objectif.montant_cible - montant_actuel

    pourcentage_atteint = (
        float(montant_actuel / objectif.montant_cible * 100) if objectif.montant_cible > 0 else 0.0
    )

    montant_mensuel_requis = None
    if objectif.date_echeance is not None:
        if montant_restant <= 0:
            montant_mensuel_requis = Decimal("0")
        else:
            montant_mensuel_requis = montant_restant / _mois_restants(objectif.date_echeance)

    return {
        "montant_actuel": montant_actuel,
        "montant_restant": montant_restant,
        "pourcentage_atteint": pourcentage_atteint,
        "montant_mensuel_requis": montant_mensuel_requis,
    }


def _recalculer_statut(objectif: ObjectifEpargne, montant_actuel: Decimal) -> None:
    """
    Statut entièrement recalculé à chaque opération, pas seulement avancé
    dans un sens : un retrait qui repasse sous la cible fait redescendre
    ATTEINT vers EN_COURS (même logique que Dette). ABANDONNE est un état
    terminal, jamais dérivé du montant.
    """
    if objectif.statut == "ABANDONNE":
        return
    objectif.statut = "ATTEINT" if montant_actuel >= objectif.montant_cible else "EN_COURS"


def creer_objectif(db: Session, id_client: int, payload: ObjectifEpargneCreate) -> ObjectifEpargne:
    """
    Crée le compte épargne dédié (solde 0 — jamais de dépôt initial direct,
    on alimente uniquement via alimenter()) puis l'objectif qui pointe
    dessus.
    """
    compte_epargne = CompteFinancier(
        id_client=id_client,
        nom=f"Épargne — {payload.nom}",
        type="EPARGNE",
        solde=Decimal("0"),
        est_actif=True,
    )
    db.add(compte_epargne)
    db.flush()

    objectif = ObjectifEpargne(
        id_client=id_client,
        id_compte_epargne=compte_epargne.id_compte,
        nom=payload.nom,
        montant_cible=payload.montant_cible,
        date_echeance=payload.date_echeance,
        statut="EN_COURS",
    )
    db.add(objectif)
    db.commit()
    db.refresh(objectif)

    comptes_service.synchroniser_compte_principal(db, id_client)
    return objectif


def lister_objectifs(db: Session, id_client: int) -> List[ObjectifEpargne]:
    return (
        db.query(ObjectifEpargne)
        .filter(ObjectifEpargne.id_client == id_client)
        .order_by(ObjectifEpargne.date_creation.desc())
        .all()
    )


def obtenir_objectif_du_client(db: Session, id_objectif: int, id_client: int) -> Optional[ObjectifEpargne]:
    return (
        db.query(ObjectifEpargne)
        .filter(ObjectifEpargne.id_objectif == id_objectif, ObjectifEpargne.id_client == id_client)
        .first()
    )


def alimenter(
    db: Session, id_client: int, id_objectif: int, montant: Decimal, id_compte_source: int
) -> ObjectifEpargne:
    """Transfert du compte source vers le compte épargne dédié — jamais une
    Transaction DEPENSE, l'épargne ne diminue pas le patrimoine net."""
    objectif = obtenir_objectif_du_client(db, id_objectif, id_client)
    if objectif is None:
        raise ObjectifIntrouvableError()
    if objectif.statut == "ABANDONNE":
        raise ObjectifVerrouilleError()

    _executer_transfert(
        db, id_client, id_compte_source, objectif.id_compte_epargne, montant, f"Épargne : {objectif.nom}"
    )

    valeurs = calculer_valeurs_objectif(objectif)
    _recalculer_statut(objectif, valeurs["montant_actuel"])
    db.commit()
    db.refresh(objectif)
    return objectif


def retirer(
    db: Session, id_client: int, id_objectif: int, montant: Decimal, id_compte_destination: int
) -> ObjectifEpargne:
    """Symétrique de alimenter() : transfert du compte épargne dédié vers un
    compte de destination choisi par le client."""
    objectif = obtenir_objectif_du_client(db, id_objectif, id_client)
    if objectif is None:
        raise ObjectifIntrouvableError()
    if objectif.statut == "ABANDONNE":
        raise ObjectifVerrouilleError()

    _executer_transfert(
        db, id_client, objectif.id_compte_epargne, id_compte_destination, montant, f"Retrait épargne : {objectif.nom}"
    )

    valeurs = calculer_valeurs_objectif(objectif)
    _recalculer_statut(objectif, valeurs["montant_actuel"])
    db.commit()
    db.refresh(objectif)
    return objectif


def abandonner(
    db: Session, id_client: int, id_objectif: int, id_compte_destination: int, request: Optional[Request] = None
) -> ObjectifEpargne:
    """
    Vide le compte épargne dédié vers un compte de destination explicite
    (pas de "compte principal" automatique : ComptePrincipal est un agrégat
    virtuel, jamais crédité/débité, il ne peut pas être la cible d'un
    Transfert). Verrouille définitivement l'objectif et désactive le
    compte dédié, qui ne pourra jamais être réutilisé (FK unique).
    """
    objectif = obtenir_objectif_du_client(db, id_objectif, id_client)
    if objectif is None:
        raise ObjectifIntrouvableError()
    if objectif.statut == "ABANDONNE":
        raise ObjectifVerrouilleError()

    # Valide la destination même si le solde est nul, pour ne jamais
    # ignorer silencieusement un id_compte_destination invalide.
    compte_destination = comptes_service.obtenir_compte_du_client(db, id_compte_destination, id_client)
    if compte_destination is None or not compte_destination.est_actif:
        raise CompteIntrouvableError()

    statut_avant = objectif.statut
    montant_actuel = objectif.compte_epargne.solde
    if montant_actuel > 0:
        _executer_transfert(
            db, id_client, objectif.id_compte_epargne, id_compte_destination, montant_actuel,
            f"Abandon de l'objectif : {objectif.nom}",
        )

    objectif.statut = "ABANDONNE"
    comptes_service.desactiver_compte(db, objectif.compte_epargne)
    db.refresh(objectif)

    enregistrer_action(
        db,
        id_utilisateur=id_client,
        action="ABANDONNER_OBJECTIF_EPARGNE",
        ressource="ObjectifEpargne",
        id_ressource=objectif.id_objectif,
        donnees_avant={"statut": statut_avant},
        donnees_apres={"statut": "ABANDONNE"},
        request=request,
    )
    return objectif
