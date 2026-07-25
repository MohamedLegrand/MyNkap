from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.plans.models import Abonnement, Plan

DUREE_CYCLE = {"MENSUEL": timedelta(days=30), "ANNUEL": timedelta(days=365)}


class PlanIntrouvableError(Exception):
    """Le plan demandé n'existe pas dans le catalogue."""


class CycleFacturationRequisError(Exception):
    """Un cycle de facturation (MENSUEL/ANNUEL) est requis pour tout plan payant."""


def lister_plans(db: Session) -> List[Plan]:
    return db.query(Plan).order_by(Plan.prix_mensuel.asc()).all()


def _obtenir_plan_gratuit(db: Session) -> Plan:
    return db.query(Plan).filter(Plan.nom == "GRATUIT").first()


def creer_abonnement_gratuit(db: Session, id_client: int) -> Abonnement:
    """
    Crée l'abonnement GRATUIT par défaut à l'inscription. Pas de commit ici
    : appelé dans la même transaction SQL que la création du Client (voir
    auth.services.creer_client), pour que le compte naisse déjà avec un
    abonnement valide.
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


def obtenir_abonnement_actif(db: Session, id_client: int) -> Abonnement:
    """
    Recalcule le statut à la lecture — jamais de tâche planifiée pour ça
    (même principe que Budget/Épargne). Aucun vrai fournisseur de paiement
    n'est encore branché : un renouvellement automatique "réussit"
    toujours pour l'instant (voir changer_plan pour le contexte), en
    attendant l'intégration réelle.
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
        if abonnement.renouvellement_auto:
            duree = DUREE_CYCLE.get(abonnement.cycle_facturation, DUREE_CYCLE["MENSUEL"])
            abonnement.date_fin = datetime.utcnow() + duree
        else:
            plan_gratuit = _obtenir_plan_gratuit(db)
            abonnement.id_plan = plan_gratuit.id_plan
            abonnement.statut = "ACTIF"
            abonnement.date_fin = None
            abonnement.cycle_facturation = None
        db.commit()
        db.refresh(abonnement)

    return abonnement


def changer_plan(
    db: Session, id_client: int, nom_plan: str, cycle_facturation: Optional[str] = None
) -> Abonnement:
    """
    Change immédiatement de plan — simulé, sans paiement réel (le
    fournisseur Mobile Money n'est pas encore choisi/intégré). Se greffera
    plus tard sans redesign : ce point d'entrée reste le même, seule la
    confirmation de paiement s'ajoutera avant l'appel.
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
