import logging
from datetime import datetime, timedelta
from typing import List, Optional
import hrpay
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.service import enregistrer_action
from app.modules.comptes import service as comptes_service
from app.modules.comptes.models import CompteFinancier
from app.modules.notifications import service as notifications_service
from app.modules.plans.models import Abonnement, PaiementAbonnement, Plan, PrixPlanDevise
from app.modules.dettes.models import Dette
from app.modules.epargne.models import ObjectifEpargne
from app.modules.tontines.models import Tontine
from app.modules.transactions.models import Transaction, TransactionRecurrente, TemplateTransaction
from app.modules.jarvis.models import Conversation

logger = logging.getLogger(__name__)

DUREE_CYCLE = {"MENSUEL": timedelta(days=30), "ANNUEL": timedelta(days=365)}
DUREE_ESSAI_GRATUIT = timedelta(days=7)
# Délai avant l'échéance à partir duquel on prévient le client du prochain
# renouvellement (voir notifier_renouvellements_proches).
DELAI_RAPPEL_RENOUVELLEMENT = timedelta(days=3)


class PlanIntrouvableError(Exception):
    """Le plan demandé n'existe pas dans le catalogue."""


class CycleFacturationRequisError(Exception):
    """Un cycle de facturation (MENSUEL/ANNUEL) est requis pour tout plan payant."""


class TelephoneOperateurRequisError(Exception):
    """phone_number et operator sont requis pour initier un paiement Mobile Money."""


class PaysOuOperateurInvalideError(Exception):
    """
    Le pays n'est pas couvert par HR-Skills Pay, ou l'opérateur demandé
    n'est pas disponible pour ce pays — validé avant l'appel réseau (voir
    hrpay.operators_for_country) pour renvoyer un 400 clair plutôt que de
    laisser HR-Skills Pay le découvrir (422 OPERATOR_NOT_AVAILABLE).
    """


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
    Essai gratuit de 7 jours à l'inscription : accès complet (plan
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
    (même principe que Budget/Épargne). À l'échéance d'un plan payant avec
    renouvellement_auto actif, tente d'abord un renouvellement réel en
    débitant le compte Abonnement dédié du client (voir
    _tenter_renouvellement_auto) — jamais un "succès" simulé sans débit
    réel. Si le renouvellement échoue (pas de compte, solde insuffisant)
    ou ne s'applique pas (essai, renouvellement_auto désactivé),
    l'abonnement revient à GRATUIT comme avant.
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
        tentative_renouvellement = abonnement.cycle_facturation is not None and abonnement.renouvellement_auto
        if tentative_renouvellement and _tenter_renouvellement_auto(db, id_client, abonnement):
            return abonnement

        if tentative_renouvellement:
            # Le renouvellement a bien été tenté (voir _tenter_renouvellement_auto)
            # mais a échoué — compte Abonnement introuvable ou solde
            # insuffisant. Le client doit le savoir avant de découvrir sans
            # explication qu'il a perdu ses fonctionnalités Premium.
            plan_precedent = abonnement.plan
            notifications_service.creer_notification_client(
                db, id_client, "RENOUVELLEMENT_ECHEC_SOLDE",
                "Abonnement non renouvelé — solde insuffisant",
                f"Le renouvellement de votre abonnement {plan_precedent.nom} n'a pas pu être effectué : "
                "le solde de votre compte Abonnement était insuffisant. Rechargez-le pour retrouver "
                "vos fonctionnalités Premium.",
            )

        plan_gratuit = _obtenir_plan_gratuit(db)
        abonnement.id_plan = plan_gratuit.id_plan
        abonnement.statut = "ACTIF"
        abonnement.date_fin = None
        abonnement.cycle_facturation = None
        db.commit()
        db.refresh(abonnement)

    return abonnement


def _tenter_renouvellement_auto(db: Session, id_client: int, abonnement: Abonnement) -> bool:
    """
    Tente de renouveler l'abonnement payant à l'identique (même plan, même
    cycle) en débitant le compte Abonnement dédié du client (voir
    comptes.service.creer_compte_abonnement) plutôt que de relancer un
    Cash-In HR-Skills Pay : le client l'a rechargé à l'avance (voir module
    recharges), donc le débit est un mouvement interne, synchrone, sans
    aller-retour Mobile Money. Renvoie False sans rien modifier si le
    compte est introuvable/inactif ou son solde insuffisant — l'appelant
    (obtenir_abonnement_actif) fait alors redescendre le client vers
    GRATUIT.
    """
    plan = abonnement.plan
    montant = plan.prix_mensuel if abonnement.cycle_facturation == "MENSUEL" else plan.prix_annuel

    compte = (
        db.query(CompteFinancier)
        .filter(
            CompteFinancier.id_client == id_client,
            CompteFinancier.type == "ABONNEMENT",
            CompteFinancier.est_actif.is_(True),
        )
        .order_by(CompteFinancier.date_creation.asc())
        .with_for_update()
        .first()
    )
    if compte is None or not compte.est_suffisant(montant):
        return False

    comptes_service.debiter_compte(compte, montant)
    db.add(Transaction(
        id_client=id_client,
        id_compte=compte.id_compte,
        id_categorie=None,
        montant=montant,
        description=f"Renouvellement automatique — plan {plan.nom} ({abonnement.cycle_facturation.lower()})",
        type="RENOUVELLEMENT_ABONNEMENT",
    ))

    abonnement.date_debut = datetime.utcnow()
    abonnement.date_fin = datetime.utcnow() + DUREE_CYCLE[abonnement.cycle_facturation]
    abonnement.statut = "ACTIF"
    # Nouveau cycle : le rappel du précédent ne concerne plus celui-ci (voir
    # notifier_renouvellements_proches).
    abonnement.rappel_renouvellement_envoye = False

    db.commit()
    db.refresh(abonnement)
    comptes_service.synchroniser_compte_principal(db, id_client)

    enregistrer_action(
        db,
        id_utilisateur=id_client,
        action="RENOUVELLEMENT_AUTO_ABONNEMENT",
        ressource="Abonnement",
        id_ressource=abonnement.id_abonnement,
        donnees_apres={"plan": plan.nom, "montant": str(montant)},
    )
    notifications_service.creer_notification_client(
        db, id_client, "ABONNEMENT_RENOUVELE",
        "Abonnement renouvelé automatiquement",
        f"Votre abonnement {plan.nom} a été renouvelé pour un cycle "
        f"{abonnement.cycle_facturation.lower()} : {montant} {compte.devise} ont été débités "
        "de votre compte Abonnement.",
    )
    return True


def notifier_renouvellements_proches(db: Session) -> int:
    """
    Tâche planifiée quotidienne (voir worker.tasks) : prévient le client
    quelques jours avant la prochaine échéance de son abonnement payant à
    renouvellement automatique actif, pour qu'il puisse vérifier ou
    recharger son compte Abonnement à temps. Ne notifie qu'une fois par
    échéance (rappel_renouvellement_envoye, remis à False à chaque nouveau
    cycle — voir changer_plan et _tenter_renouvellement_auto).
    """
    seuil = datetime.utcnow() + DELAI_RAPPEL_RENOUVELLEMENT
    a_notifier = (
        db.query(Abonnement)
        .filter(
            Abonnement.cycle_facturation.isnot(None),
            Abonnement.renouvellement_auto.is_(True),
            Abonnement.statut == "ACTIF",
            Abonnement.rappel_renouvellement_envoye.is_(False),
            Abonnement.date_fin.isnot(None),
            Abonnement.date_fin > datetime.utcnow(),
            Abonnement.date_fin <= seuil,
        )
        .all()
    )

    for abonnement in a_notifier:
        plan = abonnement.plan
        montant = plan.prix_mensuel if abonnement.cycle_facturation == "MENSUEL" else plan.prix_annuel
        notifications_service.creer_notification_client(
            db, abonnement.id_client, "RENOUVELLEMENT_PROCHE",
            "Renouvellement de votre abonnement à venir",
            f"Votre abonnement {plan.nom} sera renouvelé le {abonnement.date_fin.strftime('%d/%m/%Y')} "
            f"pour {montant} {plan.devise}, prélevés sur votre compte Abonnement. Vérifiez qu'il est "
            "suffisamment approvisionné.",
        )
        abonnement.rappel_renouvellement_envoye = True

    db.commit()
    return len(a_notifier)


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
    # Nouveau cycle : le rappel du précédent (le cas échéant) ne concerne
    # plus celui-ci (voir notifier_renouvellements_proches).
    abonnement.rappel_renouvellement_envoye = False

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


def obtenir_pays_disponibles() -> list[dict]:
    """
    Pays/devises/opérateurs Mobile Money couverts par HR-Skills Pay —
    lecture pure des données de référence embarquées dans le SDK (aucun
    appel réseau, aucun accès DB). Volontairement pas de liste recopiée
    côté MyNkap : une évolution future du SDK (nouveau pays/opérateur) est
    absorbée sans changement de code ici.
    """
    return [
        {
            "pays": info.country.value,
            "nom": info.name,
            "devise": info.currency.value,
            "operateurs": [op.value for op in info.operators],
        }
        for info in hrpay.operators_by_country()
    ]


def _valider_pays_et_operateur(pays: str, operator: str) -> str:
    """
    Vérifie que `pays` est couvert par HR-Skills Pay et que `operator` y est
    disponible. Renvoie la devise du pays (source de vérité pour le
    montant à facturer — jamais Plan.devise, qui n'est que le prix de
    référence XAF affiché sur la page publique).
    """
    try:
        pays_enum = hrpay.Country(pays)
    except ValueError:
        raise PaysOuOperateurInvalideError(f"Pays non couvert par HR-Skills Pay : {pays}.")

    operateurs_disponibles = hrpay.operators_for_country(pays_enum)
    if operator.upper() not in [op.value for op in operateurs_disponibles]:
        raise PaysOuOperateurInvalideError(
            f"Opérateur {operator} indisponible pour {pays}."
        )

    for info in hrpay.operators_by_country():
        if info.country == pays_enum:
            return info.currency.value
    raise PaysOuOperateurInvalideError(f"Pays non couvert par HR-Skills Pay : {pays}.")


def _obtenir_prix(db: Session, plan: Plan, devise: str) -> tuple:
    """
    Prix (mensuel, annuel) du plan dans la devise résolue depuis le pays
    choisi (voir _valider_pays_et_operateur) — jamais Plan.prix_mensuel/
    prix_annuel, qui restent le prix de référence XAF affiché publiquement.
    """
    prix = (
        db.query(PrixPlanDevise)
        .filter(PrixPlanDevise.id_plan == plan.id_plan, PrixPlanDevise.devise == devise)
        .first()
    )
    if prix is None:
        raise PaysOuOperateurInvalideError(f"Aucun prix défini pour {plan.nom} en {devise}.")
    return prix.prix_mensuel, prix.prix_annuel


def _appeler_hrpay_cash_in(
    phone_number: str, operator: str, montant, devise: str, country: str, id_paiement: int
) -> str:
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
            country=hrpay.Country(country),
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
    db: Session, id_client: int, nom_plan: str, cycle_facturation: str, phone_number: str, operator: str, pays: str
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

    # Résout la devise réelle depuis le pays choisi (jamais plan.devise, qui
    # n'est que le prix de référence XAF affiché sur la page publique), puis
    # le prix correspondant à cette devise.
    devise = _valider_pays_et_operateur(pays, operator)
    montant_mensuel, montant_annuel = _obtenir_prix(db, plan, devise)
    montant = montant_mensuel if cycle_facturation == "MENSUEL" else montant_annuel

    paiement = PaiementAbonnement(
        id_client=id_client,
        id_plan_demande=plan.id_plan,
        cycle_facturation=cycle_facturation,
        montant=montant,
        devise=devise,
        pays=pays,
        reference_hrpay="",
        statut="PENDING",
    )
    db.add(paiement)
    db.flush()  # pour obtenir id_paiement avant l'appel externe (idempotency_key)

    try:
        reference = _appeler_hrpay_cash_in(phone_number, operator, montant, devise, pays, paiement.id_paiement)
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


# --- Solde du wallet marchand (lecture seule — aucun retrait n'est
# possible depuis MyNkap, voir admin.service.obtenir_solde_wallet_admin) ---

def obtenir_solde_wallet() -> dict:
    """
    Solde réel du wallet marchand HR-Skills Pay — permet de savoir combien
    peut être retiré avant de tenter un Cash-Out (l'argent encore `held`,
    en attente 48h, ne peut pas financer un retrait).
    """
    try:
        with _client_hrpay() as client:
            bal = client.wallet.balance()
    except hrpay.HRPayError as erreur:
        # Sans ce catch, une clé HR-Skills Pay invalide/expirée remonte en
        # exception non gérée : FastAPI renvoie alors un 500 généré par
        # Starlette en dehors du middleware CORS, que le navigateur ne peut
        # pas lire — le frontend voit juste "Failed to fetch" au lieu du
        # vrai message d'erreur (voir historique).
        logger.warning(
            "Échec HR-Skills Pay (wallet.balance) : type=%s code=%s statut=%s message=%s",
            type(erreur).__name__, erreur.code, erreur.status_code, erreur.message,
        )
        raise ServicePaiementIndisponibleError(str(erreur))
    return {
        "devise": bal.currency,
        "disponible": bal.balance.available,
        "en_attente": bal.balance.held,
        "gele": bal.is_frozen,
    }


