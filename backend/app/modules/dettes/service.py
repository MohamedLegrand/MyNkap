from decimal import Decimal
from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.comptes import service as comptes_service
from app.modules.comptes.service import crediter_compte, debiter_compte, synchroniser_compte_principal
from app.modules.dettes.models import Dette
from app.modules.dettes.schemas import DetteCreate
from app.modules.transactions.models import Transaction

STATUTS_VERROUILLES = ("SOLDE", "PERTE")


class CompteIntrouvableError(Exception):
    """Le compte n'existe pas, n'appartient pas au client, ou est désactivé."""


class DetteIntrouvableError(Exception):
    """La dette/créance n'existe pas ou n'appartient pas au client."""


class DetteVerrouilleeError(Exception):
    """La dette/créance est SOLDE ou PERTE : plus aucune opération n'est possible."""


class TypeOperationIncompatibleError(Exception):
    """rembourser() appelé sur une CREANCE, encaisser() sur une DETTE, ou
    marquer_comme_perte() sur une DETTE (PERTE est réservé aux créances)."""


class MontantSuperieurAuRestantError(Exception):
    """Le montant dépasse ce qu'il reste à rembourser/encaisser."""


class SoldeInsuffisantError(Exception):
    """Le compte n'a pas les fonds nécessaires pour cette opération."""


def _appliquer_impact(compte, impact: Decimal) -> None:
    if impact >= 0:
        crediter_compte(compte, impact)
    else:
        debiter_compte(compte, -impact)


def lister_dettes(db: Session, id_client: int, type_: Optional[str] = None) -> List[Dette]:
    query = db.query(Dette).filter(Dette.id_client == id_client)
    if type_ is not None:
        query = query.filter(Dette.type == type_)
    return query.order_by(Dette.date_creation.desc()).all()


def obtenir_dette_du_client(db: Session, id_dette: int, id_client: int) -> Optional[Dette]:
    return db.query(Dette).filter(Dette.id_dette == id_dette, Dette.id_client == id_client).first()


def creer_dette(db: Session, id_client: int, payload: DetteCreate) -> Dette:
    """
    Crée une dette reçue ou une créance accordée. La transaction d'origine
    (DETTE_RECUE ou CREANCE_ACCORDEE) crédite/débite le compte dans la même
    opération SQL — jamais un solde qui apparaît/disparaît sans origine
    tracée, même pour ce cas particulier hors DEPENSE/REVENU.
    """
    compte = comptes_service.obtenir_compte_du_client(db, payload.id_compte, id_client, for_update=True)
    if compte is None or not compte.est_actif:
        raise CompteIntrouvableError()

    # Une créance accordée débite le compte : il faut avoir l'argent à prêter.
    # Une dette reçue crédite le compte : aucune vérification de solde requise.
    if payload.type == "CREANCE" and not compte.est_suffisant(payload.montant_total):
        raise SoldeInsuffisantError()

    dette = Dette(
        id_client=id_client,
        id_compte=compte.id_compte,
        nom=payload.nom,
        type=payload.type,
        montant_total=payload.montant_total,
        montant_rembourse=Decimal("0"),
        personne_impliquee=payload.personne_impliquee,
        date_echeance=payload.date_echeance,
        statut="EN_COURS",
    )
    db.add(dette)
    db.flush()

    type_transaction = "DETTE_RECUE" if payload.type == "DETTE" else "CREANCE_ACCORDEE"
    verbe = "Dette reçue" if payload.type == "DETTE" else "Créance accordée"
    origine = Transaction(
        id_client=id_client,
        id_compte=compte.id_compte,
        id_categorie=None,
        id_dette=dette.id_dette,
        montant=payload.montant_total,
        type=type_transaction,
        description=f"{verbe} : {payload.nom}",
    )
    db.add(origine)
    db.flush()

    dette.id_transaction_origine = origine.id_transaction
    _appliquer_impact(compte, origine.calculer_impact())

    db.commit()
    db.refresh(dette)

    synchroniser_compte_principal(db, id_client)
    return dette


def _recalculer_montant_rembourse(db: Session, dette: Dette) -> None:
    """
    Recalcule montant_rembourse depuis la somme des transactions de
    remboursement/encaissement liées — jamais un compteur incrémenté à la
    main, pour ne jamais désynchroniser l'affiché du réellement survenu.
    """
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.id_dette == dette.id_dette,
            Transaction.type.in_(("REMBOURSEMENT_DETTE", "ENCAISSEMENT_CREANCE")),
        )
        .all()
    )
    dette.montant_rembourse = sum((t.montant for t in transactions), Decimal("0"))

    if dette.montant_rembourse <= 0:
        dette.statut = "EN_COURS"
    elif dette.montant_rembourse < dette.montant_total:
        dette.statut = "PARTIELLEMENT_REMBOURSE"
    else:
        dette.marquer_comme_solde()


def _operer(
    db: Session,
    id_client: int,
    id_dette: int,
    montant: Decimal,
    id_compte: int,
    type_attendu: str,
    type_transaction: str,
    verbe: str,
) -> Dette:
    dette = obtenir_dette_du_client(db, id_dette, id_client)
    if dette is None:
        raise DetteIntrouvableError()

    if dette.type != type_attendu:
        raise TypeOperationIncompatibleError()

    if dette.statut in STATUTS_VERROUILLES:
        raise DetteVerrouilleeError()

    if montant > dette.get_montant_restant():
        raise MontantSuperieurAuRestantError()

    compte = comptes_service.obtenir_compte_du_client(db, id_compte, id_client, for_update=True)
    if compte is None or not compte.est_actif:
        raise CompteIntrouvableError()

    # Rembourser une dette est une sortie d'argent réelle : il faut les
    # fonds. Encaisser une créance est une entrée d'argent : aucune
    # vérification de solde n'est nécessaire.
    if type_transaction == "REMBOURSEMENT_DETTE" and not compte.est_suffisant(montant):
        raise SoldeInsuffisantError()

    transaction = Transaction(
        id_client=id_client,
        id_compte=compte.id_compte,
        id_categorie=None,
        id_dette=dette.id_dette,
        montant=montant,
        type=type_transaction,
        description=f"{verbe} de la dette #{dette.id_dette}",
    )
    db.add(transaction)
    db.flush()

    _appliquer_impact(compte, transaction.calculer_impact())
    _recalculer_montant_rembourse(db, dette)

    db.commit()
    db.refresh(dette)

    synchroniser_compte_principal(db, id_client)
    return dette


def rembourser(db: Session, id_client: int, id_dette: int, montant: Decimal, id_compte: int) -> Dette:
    return _operer(db, id_client, id_dette, montant, id_compte, "DETTE", "REMBOURSEMENT_DETTE", "Remboursement")


def encaisser(db: Session, id_client: int, id_dette: int, montant: Decimal, id_compte: int) -> Dette:
    return _operer(db, id_client, id_dette, montant, id_compte, "CREANCE", "ENCAISSEMENT_CREANCE", "Encaissement")


def marquer_comme_perte(db: Session, id_client: int, id_dette: int, request: Optional[Request] = None) -> Dette:
    """
    Constate qu'une créance est irrécouvrable. Manuel uniquement (jamais
    automatique), réservé aux créances : une dette, le client la doit quoi
    qu'il arrive. Verrouille définitivement l'objet, comme SOLDE.
    """
    dette = obtenir_dette_du_client(db, id_dette, id_client)
    if dette is None:
        raise DetteIntrouvableError()
    if dette.type != "CREANCE":
        raise TypeOperationIncompatibleError()
    if dette.statut in STATUTS_VERROUILLES:
        raise DetteVerrouilleeError()

    statut_avant = dette.statut
    dette.statut = "PERTE"
    db.commit()
    db.refresh(dette)

    enregistrer_action(
        db,
        id_utilisateur=id_client,
        action="MARQUER_PERTE",
        ressource="Dette",
        id_ressource=dette.id_dette,
        donnees_avant={"statut": statut_avant},
        donnees_apres={"statut": "PERTE"},
        request=request,
    )
    return dette
