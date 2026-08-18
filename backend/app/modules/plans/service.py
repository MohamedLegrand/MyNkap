import logging
from datetime import datetime, timedelta
from typing import List, Optional
import hrpay
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.service import enregistrer_action
from app.modules.notifications import service as notifications_service
from app.modules.plans.models import Abonnement, PaiementAbonnement, Plan
from app.modules.dettes.models import Dette
from app.modules.epargne.models import ObjectifEpargne
from app.modules.tontines.models import Tontine
from app.modules.transactions.models import TransactionRecurrente, TemplateTransaction
from app.modules.jarvis.models import Conversation

logger = logging.getLogger(__name__)

DUREE_CYCLE = {"MENSUEL": timedelta(days=30), "ANNUEL": timedelta(days=365)}
DUREE_ESSAI_GRATUIT = timedelta(days=30)


class PlanIntrouvableError(Exception):
    """Le plan demandé n'existe pas dans le catalogue."""


class CycleFacturationRequisError(Exception):
    """Un cycle de facturation (MENSUEL/ANNUEL) est requis pour tout plan payant."""


class TelephoneOperateurRequisError(Exception):
    """phone_number et operator sont requis pour initier un paiement Mobile Money."""


class ServicePaiementIndisponibleError(Exception):
    """L'appel à HR-Skills Pay a échoué (réseau, clé invalide, quota...)."""


class PaiementRefuseError(Exception):
    """
    HR-Skills Pay a rejeté la demande à cause des informations fournies par
    le client (numéro/opérateur incohérents...) — voir CODES_ERREUR_CLIENT.
    Distinct de ServicePaiementIndisponibleError : ce n'est pas une panne,
    le client peut corriger sa saisie et réessayer immédiatement.
    """


class EssaiInactifError(Exception):
    """Le client n'est pas (ou plus) en période d'essai — rien à confirmer."""


def lister_plans(db: Session) -> List[Plan]:
    return db.query(Plan).order_by(Plan.prix_mensuel.asc()).all()


def _obtenir_plan_gratuit(db: Session) -> Plan:
    return db.query(Plan).filter(Plan.nom == "GRATUIT").first()


def _obtenir_plan_premium(db: Session) -> Plan:
    return db.query(Plan).filter(Plan.nom == "PREMIUM").first()


def creer_abonnement_gratuit(db: Session, id_client: int) -> Abonnement:
    """
    Crée un abonnement GRATUIT nu. Pas de commit ici : appelée soit comme
    filet de sécurité pour un client déjà existant sans abonnement (voir
    obtenir_abonnement_actif), soit à l'échéance d'un essai/plan payant.
    """
    plan_gratuit = _obtenir_plan_gratuit(db)
    abonnement = Abonnement(
        id_client=id_client,
        id_plan=plan_gratuit.id_plan,
        statut="ACTIF",
        date_fin=None,
        cycle_facturation=None,
    )
    db.add(abonnement)
    return abonnement


def creer_abonnement_essai(db: Session, id_client: int) -> Abonnement:
    """
    Essai gratuit de 30 jours à l'inscription : accès complet (plan
    PREMIUM, JARVIS inclus) sans paiement ni engagement. Pas de commit ici
    : appelé dans la même transaction SQL que la création du Client (voir
    auth.services.creer_client), pour que le compte naisse déjà avec un
    abonnement valide. renouvellement_auto=False car il n'y a aucun
    paiement à débiter à l'échéance : obtenir_abonnement_actif fait
    systématiquement redescendre le client vers GRATUIT à la date_fin,
    jamais vers un plan payant sans paiement réel confirmé.
    """
    plan_premium = _obtenir_plan_premium(db)
    abonnement = Abonnement(
        id_client=id_client,
        id_plan=plan_premium.id_plan,
        statut="ESSAI",
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + DUREE_ESSAI_GRATUIT,
        cycle_facturation=None,
        renouvellement_auto=False,
    )
    db.add(abonnement)
    return abonnement


def obtenir_abonnement_actif(db: Session, id_client: int) -> Abonnement:
    """
    Recalcule le statut à la lecture — jamais de tâche planifiée pour ça
    (même principe que Budget/Épargne). Depuis l'intégration HR-Skills Pay,
    aucun renouvellement n'est simulé : simuler un "succès" sans avoir
    réellement tenté de débiter le client serait mensonger. À l'échéance,
    l'abonnement revient donc systématiquement à GRATUIT — le
    renouvellement automatique réel (relancer un Cash-In au bon moment)
    reste un chantier séparé, pas encore construit.
    """
    abonnement = db.query(Abonnement).filter(Abonnement.id_client == id_client).first()
    if abonnement is None:
        # Filet de sécurité pour un client déjà existant avant ce module —
        # ne devrait plus se produire après la migration de backfill.
        abonnement = creer_abonnement_gratuit(db, id_client)
        db.commit()
        db.refresh(abonnement)
        return abonnement

    if abonnement.date_fin is not None and abonnement.date_fin <= datetime.utcnow():
        plan_gratuit = _obtenir_plan_gratuit(db)
        abonnement.id_plan = plan_gratuit.id_plan
        abonnement.statut = "ACTIF"
        abonnement.date_fin = None
        abonnement.cycle_facturation = None
        db.commit()
        db.refresh(abonnement)

    return abonnement


def compter_donnees_verrouillees(db: Session, id_client: int) -> dict:
    """
    Compte les données déjà existantes du client dans chaque module à
    palier (dettes, épargne, tontines, récurrentes, templates, JARVIS) —
    qu'elles soient actuellement accessibles ou non avec le forfait actif.
    Un changement de palier (fin d'essai, downgrade, échec de paiement) ne
    supprime jamais ces données, seul l'accès via l'API est restreint (voir
    dependencies.exiger_fonctionnalite) ; ces compteurs permettent au
    frontend d'afficher « vous avez N dettes enregistrées » plutôt que de
    faire disparaître le module sans explication. Ne renvoie que des
    comptes, jamais les données elles-mêmes : accessible quel que soit le
    forfait (voir router.obtenir_donnees_verrouillees, non gaté).
    """
    return {
        "dettes": db.query(Dette).filter(Dette.id_client == id_client, Dette.est_actif.is_(True)).count(),
        "epargne": db.query(ObjectifEpargne).filter(ObjectifEpargne.id_client == id_client).count(),
        "tontines": db.query(Tontine).filter(Tontine.id_client == id_client).count(),
        "transactions_recurrentes": db.query(TransactionRecurrente).filter(
            TransactionRecurrente.id_client == id_client, TransactionRecurrente.est_active.is_(True)
        ).count(),
        "templates": db.query(TemplateTransaction).filter(
            TemplateTransaction.id_client == id_client, TemplateTransaction.est_actif.is_(True)
        ).count(),
        "jarvis": db.query(Conversation).filter(Conversation.id_client == id_client).count(),
    }


def notifier_essai_actif(db: Session, id_client: int) -> None:
    """
    Crée une notification confirmant au client qu'il bénéficie bien de
    l'essai Premium en cours — déclenchée depuis le bouton "Profiter de mes
    30 jours Premium" du tableau de bord (jamais automatiquement à
    l'inscription : c'est une confirmation à la demande, pas une alerte
    système).
    """
    abonnement = obtenir_abonnement_actif(db, id_client)
    if abonnement.statut != "ESSAI" or abonnement.date_fin is None:
        raise EssaiInactifError()

    jours_restants = max(0, (abonnement.date_fin - datetime.utcnow()).days + 1)
    notifications_service.creer_notification_client(
        db,
        id_client,
        "ESSAI_PREMIUM_ACTIF",
        "Accès Premium activé",
        f"Vous avez bien accès à toutes les fonctionnalités Premium (JARVIS inclus) pendant encore {jours_restants} jour{'s' if jours_restants > 1 else ''}.",
    )


def changer_plan(
    db: Session, id_client: int, nom_plan: str, cycle_facturation: Optional[str] = None
) -> Abonnement:
    """
    Change immédiatement de plan en base. Pour GRATUIT, appelée
    directement (aucun paiement requis pour revenir au plan gratuit). Pour
    un plan payant, n'est appelée qu'une fois un paiement HR-Skills Pay
    confirmé SUCCESS (voir verifier_paiements_en_attente) — jamais
    directement depuis un endpoint pour un plan payant.
    """
    plan = db.query(Plan).filter(Plan.nom == nom_plan).first()
    if plan is None:
        raise PlanIntrouvableError()

    abonnement = obtenir_abonnement_actif(db, id_client)
    donnees_avant = {"plan": abonnement.plan.nom, "statut": abonnement.statut}

    abonnement.id_plan = plan.id_plan
    abonnement.statut = "ACTIF"
    abonnement.date_debut = datetime.utcnow()
    abonnement.renouvellement_auto = True

    if nom_plan == "GRATUIT":
        abonnement.date_fin = None
        abonnement.cycle_facturation = None
    else:
        if cycle_facturation not in DUREE_CYCLE:
            raise CycleFacturationRequisError()
        abonnement.cycle_facturation = cycle_facturation
        abonnement.date_fin = datetime.utcnow() + DUREE_CYCLE[cycle_facturation]

    db.commit()
    db.refresh(abonnement)

    enregistrer_action(
        db,
        id_utilisateur=id_client,
        action="CHANGER_PLAN",
        ressource="Abonnement",
        id_ressource=abonnement.id_abonnement,
        donnees_avant=donnees_avant,
        donnees_apres={"plan": plan.nom, "statut": "ACTIF"},
    )
    return abonnement


def annuler_renouvellement(db: Session, id_client: int) -> Abonnement:
    """
    Arrête le renouvellement futur sans couper l'accès immédiatement : le
    client garde son plan jusqu'à date_fin, qui bascule alors
    automatiquement vers GRATUIT (voir obtenir_abonnement_actif).
    """
    abonnement = obtenir_abonnement_actif(db, id_client)
    abonnement.renouvellement_auto = False
    abonnement.statut = "ANNULE"
    db.commit()
    db.refresh(abonnement)
    return abonnement


# --- Paiement Mobile Money (HR-Skills Pay) ---

def _client_hrpay() -> hrpay.HRPayClient:
    return hrpay.HRPayClient(settings.HRPAY_PUBLIC_KEY, settings.HRPAY_SECRET_KEY)


def _appeler_hrpay_cash_in(phone_number: str, operator: str, montant, devise: str, id_paiement: int) -> str:
    """
    Isolée dans sa propre fonction pour rester mockable en test (même
    principe que jarvis._appeler_groq) — aucun test ne doit jamais
    déclencher un vrai Cash-In. idempotency_key basé sur id_paiement :
    un retry réseau sur la même requête ne débite jamais deux fois.
    """
    with _client_hrpay() as client:
        tx = client.cash_in.mobile_money(
            phone_number=phone_number,
            # Le SDK exige l'opérateur en majuscules (ex. "MTN"), malgré
            # la documentation qui suggère une string libre insensible à
            # la casse — ce n'est pas le cas en pratique.
            operator=operator.upper(),
            amount=int(montant),
            currency=devise,
            idempotency_key=f"abonnement-{id_paiement}",
        )
    return tx.reference


def _verifier_statut_hrpay(reference: str) -> str:
    """
    Isolée pour rester mockable en test — voir _appeler_hrpay_cash_in.
    Le champ `status` de Transaction est une chaîne simple (pas un enum,
    contrairement à ce que la doc laisse penser pour CashInResponse) —
    .value géré en défensif seulement s'il s'agit bien d'un enum.
    """
    with _client_hrpay() as client:
        statut = client.transactions.status(reference).status
        return statut.value if hasattr(statut, "value") else statut


def obtenir_paiement_du_client(db: Session, id_paiement: int, id_client: int) -> Optional[PaiementAbonnement]:
    return (
        db.query(PaiementAbonnement)
        .filter(PaiementAbonnement.id_paiement == id_paiement, PaiementAbonnement.id_client == id_client)
        .first()
    )


def initier_paiement_plan(
    db: Session, id_client: int, nom_plan: str, cycle_facturation: str, phone_number: str, operator: str
) -> PaiementAbonnement:
    """
    Démarre un paiement Mobile Money réel pour souscrire à un plan payant.
    Le plan n'est PAS changé ici — seulement une fois que
    verifier_paiements_en_attente() aura confirmé le SUCCESS (voir la
    tâche Celery périodique, worker.tasks). N'est jamais appelée pour
    GRATUIT (voir router : GRATUIT passe par changer_plan directement).
    """
    plan = db.query(Plan).filter(Plan.nom == nom_plan).first()
    if plan is None:
        raise PlanIntrouvableError()
    if cycle_facturation not in DUREE_CYCLE:
        raise CycleFacturationRequisError()
    if not phone_number or not operator:
        raise TelephoneOperateurRequisError()

    montant = plan.prix_mensuel if cycle_facturation == "MENSUEL" else plan.prix_annuel

    paiement = PaiementAbonnement(
        id_client=id_client,
        id_plan_demande=plan.id_plan,
        cycle_facturation=cycle_facturation,
        montant=montant,
        devise=plan.devise,
        reference_hrpay="",
        statut="PENDING",
    )
    db.add(paiement)
    db.flush()  # pour obtenir id_paiement avant l'appel externe (idempotency_key)

    try:
        reference = _appeler_hrpay_cash_in(phone_number, operator, montant, plan.devise, paiement.id_paiement)
    except hrpay.ValidationError as erreur:
        # Payload rejeté par HR-Skills Pay (HTTP 400/422) : c'est le seul
        # cas structurellement imputable à la saisie du client (le SDK a sa
        # propre classe pour ça, indépendamment du code renvoyé) — les
        # autres HRPayError (APIError, réseau, quota...) restent
        # génériques ci-dessous, car imputables à HR-Skills Pay, pas au
        # client.
        db.rollback()
        logger.warning(
            "Paiement rejeté (validation HR-Skills Pay) : statut=%s message=%s issues=%s",
            erreur.status_code, erreur.message, erreur.issues,
        )
        raise PaiementRefuseError("Le numéro de téléphone fourni est invalide.")
    except hrpay.HRPayError as erreur:
        db.rollback()
        # Toujours logué côté serveur : le message générique renvoyé au
        # client (ci-dessous) ne doit jamais divulguer les détails internes
        # HR-Skills Pay, mais un développeur doit pouvoir diagnostiquer sans
        # deviner (voir historique : une simple instabilité de l'API HR-Skills
        # Pay était impossible à distinguer d'une vraie panne sans ce log).
        logger.warning(
            "Échec HR-Skills Pay (cash-in) : type=%s code=%s statut=%s message=%s",
            type(erreur).__name__, erreur.code, erreur.status_code, erreur.message,
        )
        raise ServicePaiementIndisponibleError(str(erreur))

    paiement.reference_hrpay = reference
    db.commit()
    db.refresh(paiement)
    return paiement


def verifier_paiements_en_attente(db: Session) -> int:
    """
    Tâche planifiée (~toutes les 20s, voir worker.tasks) : interroge
    HR-Skills Pay pour chaque paiement encore PENDING et finalise le
    changement de plan dès que SUCCESS est confirmé. HR-Skills Pay fait
    lui-même expirer une transaction non confirmée sous 10 min (FAILED
    côté leur API) — inutile de dupliquer cette logique de timeout ici.
    """
    en_attente = db.query(PaiementAbonnement).filter(PaiementAbonnement.statut == "PENDING").all()
    nb_traites = 0

    for paiement in en_attente:
        try:
            statut = _verifier_statut_hrpay(paiement.reference_hrpay)
        except hrpay.HRPayError:
            continue  # on retentera au prochain passage

        if statut == "SUCCESS":
            nom_plan = paiement.plan_demande.nom
            changer_plan(db, paiement.id_client, nom_plan, paiement.cycle_facturation)
            paiement.statut = "SUCCESS"
            paiement.date_confirmation = datetime.utcnow()
            db.commit()
            nb_traites += 1

            notifications_service.creer_notification_client(
                db, paiement.id_client, "PAIEMENT_CONFIRME",
                "Paiement confirmé",
                f"Votre paiement de {paiement.montant} {paiement.devise} a été confirmé — "
                f"vous êtes maintenant sur le plan {nom_plan}.",
            )
            notifications_service.creer_notification_admins(
                db, "PAIEMENT_RECU",
                "Paiement reçu",
                f"{paiement.client.first_name} {paiement.client.last_name} ({paiement.client.email}) "
                f"a payé {paiement.montant} {paiement.devise} pour le plan {nom_plan}.",
                lien="/admin?tab=subscriptions",
            )
        elif statut in ("FAILED", "REFUNDED"):
            paiement.statut = "FAILED"
            db.commit()
            nb_traites += 1

            notifications_service.creer_notification_client(
                db, paiement.id_client, "PAIEMENT_ECHEC",
                "Paiement refusé",
                f"Votre paiement de {paiement.montant} {paiement.devise} pour le plan "
                f"{paiement.plan_demande.nom} a échoué ou expiré. Vous pouvez réessayer.",
            )
        # PENDING ou HOLD (revue AML) : rien à faire, on retentera au
        # prochain passage.

    return nb_traites
