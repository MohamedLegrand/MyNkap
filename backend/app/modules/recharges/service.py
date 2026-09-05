import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import hrpay
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.comptes.models import CompteFinancier
from app.modules.comptes.service import crediter_compte, synchroniser_compte_principal
from app.modules.notifications import service as notifications_service
from app.modules.recharges.models import RechargeCompte
from app.modules.transactions.models import Transaction

logger = logging.getLogger(__name__)


class CompteIntrouvableError(Exception):
    """Le compte n'existe pas, n'appartient pas au client, ou est désactivé."""


class CompteNonRechargeableError(Exception):
    """
    Seul le compte ABONNEMENT peut être rechargé via Mobile Money : les
    autres comptes (mobile money, bancaire, espèces, épargne) ne sont que
    des soldes suivis dans l'app, jamais reliés à un vrai paiement HR-Skills
    Pay entrant — les alimenter se fait via une transaction (dépôt/revenu),
    pas une recharge.
    """


class PaysOuOperateurInvalideError(Exception):
    """
    Le pays n'est pas couvert par HR-Skills Pay, ou l'opérateur demandé
    n'est pas disponible pour ce pays — validé avant l'appel réseau, comme
    plans.service._valider_pays_et_operateur (même principe, dupliqué
    volontairement : chaque module reste autonome, voir tontines._avancer_date
    pour le même choix déjà fait ailleurs dans le projet).
    """


class TelephoneOperateurRequisError(Exception):
    """phone_number et operator sont requis pour initier une recharge Mobile Money."""


class ServicePaiementIndisponibleError(Exception):
    """L'appel à HR-Skills Pay a échoué (réseau, clé invalide, quota...)."""


class PaiementRefuseError(Exception):
    """
    HR-Skills Pay a rejeté la demande à cause des informations fournies par
    le client (numéro/opérateur incohérents...) — le client peut corriger
    sa saisie et réessayer immédiatement.
    """


def _client_hrpay() -> hrpay.HRPayClient:
    return hrpay.HRPayClient(settings.HRPAY_PUBLIC_KEY, settings.HRPAY_SECRET_KEY)


def _valider_pays_et_operateur(pays: str, operator: str) -> str:
    """Renvoie la devise réelle du pays choisi — jamais la devise déclarée
    du compte, qui n'est qu'une préférence d'affichage côté client."""
    try:
        pays_enum = hrpay.Country(pays)
    except ValueError:
        raise PaysOuOperateurInvalideError(f"Pays non couvert par HR-Skills Pay : {pays}.")

    operateurs_disponibles = hrpay.operators_for_country(pays_enum)
    if operator.upper() not in [op.value for op in operateurs_disponibles]:
        raise PaysOuOperateurInvalideError(f"Opérateur {operator} indisponible pour {pays}.")

    for info in hrpay.operators_by_country():
        if info.country == pays_enum:
            return info.currency.value
    raise PaysOuOperateurInvalideError(f"Pays non couvert par HR-Skills Pay : {pays}.")


def _appeler_hrpay_cash_in(
    phone_number: str, operator: str, montant, devise: str, country: str, id_recharge: int
) -> str:
    """Isolée pour rester mockable en test — miroir de
    plans.service._appeler_hrpay_cash_in. idempotency_key basé sur
    id_recharge : un retry réseau ne débite jamais deux fois le client."""
    with _client_hrpay() as client:
        tx = client.cash_in.mobile_money(
            phone_number=phone_number,
            operator=operator.upper(),
            amount=int(montant),
            currency=devise,
            country=hrpay.Country(country),
            idempotency_key=f"recharge-{id_recharge}",
        )
    return tx.reference


def _verifier_statut_hrpay(reference: str) -> str:
    with _client_hrpay() as client:
        statut = client.transactions.status(reference).status
        return statut.value if hasattr(statut, "value") else statut


def initier_recharge(
    db: Session, id_client: int, id_compte: int, montant: Decimal, phone_number: str, operator: str, pays: str
) -> RechargeCompte:
    """
    Démarre une recharge Mobile Money réelle. Le compte n'est PAS crédité
    ici — seulement une fois que verifier_recharges_en_attente() aura
    confirmé le SUCCESS (tâche planifiée, voir worker.tasks).
    """
    compte = (
        db.query(CompteFinancier)
        .filter(
            CompteFinancier.id_compte == id_compte,
            CompteFinancier.id_client == id_client,
            CompteFinancier.est_actif.is_(True),
        )
        .first()
    )
    if compte is None:
        raise CompteIntrouvableError()
    if compte.type != "ABONNEMENT":
        raise CompteNonRechargeableError()
    if not phone_number or not operator:
        raise TelephoneOperateurRequisError()

    devise = _valider_pays_et_operateur(pays, operator)

    recharge = RechargeCompte(
        id_client=id_client,
        id_compte=id_compte,
        montant=montant,
        devise=devise,
        pays=pays,
        reference_hrpay="",
        statut="PENDING",
    )
    db.add(recharge)
    db.flush()  # pour obtenir id_recharge avant l'appel externe (idempotency_key)

    try:
        reference = _appeler_hrpay_cash_in(phone_number, operator, montant, devise, pays, recharge.id_recharge)
    except hrpay.ValidationError as erreur:
        db.rollback()
        logger.warning(
            "Recharge rejetée (validation HR-Skills Pay) : statut=%s message=%s issues=%s",
            erreur.status_code, erreur.message, erreur.issues,
        )
        raise PaiementRefuseError("Le numéro de téléphone fourni est invalide.")
    except hrpay.HRPayError as erreur:
        db.rollback()
        logger.warning(
            "Échec HR-Skills Pay (recharge) : type=%s code=%s statut=%s message=%s",
            type(erreur).__name__, erreur.code, erreur.status_code, erreur.message,
        )
        raise ServicePaiementIndisponibleError(str(erreur))

    recharge.reference_hrpay = reference
    db.commit()
    db.refresh(recharge)
    return recharge


def lister_recharges_du_client(db: Session, id_client: int) -> List[RechargeCompte]:
    return (
        db.query(RechargeCompte)
        .filter(RechargeCompte.id_client == id_client)
        .order_by(RechargeCompte.date_creation.desc())
        .all()
    )


def obtenir_recharge_du_client(db: Session, id_recharge: int, id_client: int) -> Optional[RechargeCompte]:
    return (
        db.query(RechargeCompte)
        .filter(RechargeCompte.id_recharge == id_recharge, RechargeCompte.id_client == id_client)
        .first()
    )


def verifier_recharges_en_attente(db: Session) -> int:
    """
    Tâche planifiée (~toutes les 20s, voir worker.tasks) : interroge
    HR-Skills Pay pour chaque recharge encore PENDING et, dès SUCCESS
    confirmé, crédite réellement le compte via une Transaction DEPOT_INITIAL
    — même traitement que le dépôt initial à la création d'un compte
    (comptes.service.creer_compte) : montant d'origine réelle et traçable,
    jamais de catégorie forcée sur un versement qui n'est ni une dépense ni
    un revenu catégorisable par le client.
    """
    en_attente = db.query(RechargeCompte).filter(RechargeCompte.statut == "PENDING").all()
    nb_traites = 0

    for recharge in en_attente:
        try:
            statut = _verifier_statut_hrpay(recharge.reference_hrpay)
        except hrpay.HRPayError:
            continue  # on retentera au prochain passage

        if statut == "SUCCESS":
            compte = (
                db.query(CompteFinancier)
                .filter(CompteFinancier.id_compte == recharge.id_compte)
                .with_for_update()
                .first()
            )
            crediter_compte(compte, recharge.montant)
            transaction = Transaction(
                id_client=recharge.id_client,
                id_compte=recharge.id_compte,
                id_categorie=None,
                montant=recharge.montant,
                description=f"Recharge Mobile Money ({recharge.pays})",
                type="DEPOT_INITIAL",
            )
            db.add(transaction)
            db.flush()

            recharge.statut = "SUCCESS"
            recharge.id_transaction = transaction.id_transaction
            recharge.date_confirmation = datetime.utcnow()
            db.commit()
            synchroniser_compte_principal(db, recharge.id_client)
            nb_traites += 1

            notifications_service.creer_notification_client(
                db, recharge.id_client, "RECHARGE_CONFIRMEE",
                "Recharge confirmée",
                f"Votre recharge de {recharge.montant} {recharge.devise} a bien été créditée sur votre compte.",
            )
        elif statut in ("FAILED", "REFUNDED"):
            recharge.statut = "FAILED"
            db.commit()
            nb_traites += 1

            notifications_service.creer_notification_client(
                db, recharge.id_client, "RECHARGE_ECHEC",
                "Recharge refusée",
                f"Votre recharge de {recharge.montant} {recharge.devise} a échoué ou expiré. Vous pouvez réessayer.",
            )
        # PENDING ou HOLD (revue AML) : rien à faire, on retentera au
        # prochain passage.

    return nb_traites
