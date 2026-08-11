import calendar
from datetime import date as date_type, datetime
from typing import List, Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.modules.audit.service import enregistrer_action
from app.modules.tontines.models import CotisationTour, MembreTontine, Tontine, TourTontine
from app.modules.tontines.schemas import TontineCreate

STATUTS_VERROUILLES = ("TERMINEE", "ANNULEE")


class TontineIntrouvableError(Exception):
    """La tontine n'existe pas ou n'appartient pas au client."""


class TourIntrouvableError(Exception):
    """Le tour n'existe pas ou n'appartient pas à cette tontine."""


class CotisationIntrouvableError(Exception):
    """Aucune cotisation attendue de ce membre sur ce tour."""


class TontineVerrouilleeError(Exception):
    """La tontine est TERMINEE ou ANNULEE : plus aucune opération n'est possible."""


class TourNonActifError(Exception):
    """Seul le tour EN_COURS peut être clôturé — les autres sont A_VENIR ou déjà TERMINE."""


class TourIncompletError(Exception):
    """Toutes les cotisations du tour doivent être versées avant de le clôturer."""


def _avancer_date(date_actuelle: date_type, frequence: str) -> date_type:
    """Même logique que transactions.service._avancer_date (HEBDOMADAIRE/
    MENSUELLE uniquement ici) : chaque module reste autonome, pas de
    dépendance croisée pour une fonction aussi courte."""
    if frequence == "HEBDOMADAIRE":
        return date_type.fromordinal(date_actuelle.toordinal() + 7)

    mois_total = date_actuelle.month - 1 + 1
    annee = date_actuelle.year + mois_total // 12
    mois = mois_total % 12 + 1
    dernier_jour_du_mois = calendar.monthrange(annee, mois)[1]
    jour = min(date_actuelle.day, dernier_jour_du_mois)
    return date_type(annee, mois, jour)


def creer_tontine(db: Session, id_client: int, payload: TontineCreate) -> Tontine:
    """
    Crée la tontine, ses membres (ordre = position dans la liste fournie),
    puis génère automatiquement un tour par membre (rotation complète) et
    une cotisation attendue par membre et par tour. Le premier tour démarre
    EN_COURS, les suivants A_VENIR — voir cloturer_tour() pour la
    progression.
    """
    tontine = Tontine(
        id_client=id_client,
        nom=payload.nom,
        montant_cotisation=payload.montant_cotisation,
        devise=payload.devise,
        frequence=payload.frequence,
        date_debut=payload.date_debut,
        statut="ACTIVE",
    )
    db.add(tontine)
    db.flush()

    membres = [
        MembreTontine(id_tontine=tontine.id_tontine, nom=m.nom, telephone=m.telephone, ordre=i + 1)
        for i, m in enumerate(payload.membres)
    ]
    db.add_all(membres)
    db.flush()

    date_tour = payload.date_debut
    for numero, membre_beneficiaire in enumerate(membres, start=1):
        if numero > 1:
            date_tour = _avancer_date(date_tour, payload.frequence)
        tour = TourTontine(
            id_tontine=tontine.id_tontine,
            numero=numero,
            id_membre_beneficiaire=membre_beneficiaire.id_membre,
            date_prevue=date_tour,
            statut="EN_COURS" if numero == 1 else "A_VENIR",
        )
        db.add(tour)
        db.flush()

        db.add_all([
            CotisationTour(id_tour=tour.id_tour, id_membre=m.id_membre, est_versee=False)
            for m in membres
        ])

    db.commit()
    db.refresh(tontine)
    return tontine


def lister_tontines(db: Session, id_client: int) -> List[Tontine]:
    return (
        db.query(Tontine)
        .filter(Tontine.id_client == id_client)
        .order_by(Tontine.date_creation.desc())
        .all()
    )


def obtenir_tontine_du_client(db: Session, id_tontine: int, id_client: int) -> Optional[Tontine]:
    return (
        db.query(Tontine)
        .filter(Tontine.id_tontine == id_tontine, Tontine.id_client == id_client)
        .first()
    )


def _obtenir_tour(tontine: Tontine, id_tour: int) -> TourTontine:
    tour = next((t for t in tontine.tours if t.id_tour == id_tour), None)
    if tour is None:
        raise TourIntrouvableError()
    return tour


def marquer_cotisation(
    db: Session, id_client: int, id_tontine: int, id_tour: int, id_membre: int, est_versee: bool
) -> Tontine:
    """
    Coche/décoche manuellement le versement d'un membre pour un tour donné
    — reflète un paiement réel effectué hors de l'application (cash,
    Mobile Money entre les membres), jamais un mouvement simulé côté
    MyNkap. Peut s'appliquer à n'importe quel tour non verrouillé (pas
    seulement le tour EN_COURS), pour rattraper une cotisation versée en
    avance ou en retard.
    """
    tontine = obtenir_tontine_du_client(db, id_tontine, id_client)
    if tontine is None:
        raise TontineIntrouvableError()
    if tontine.statut in STATUTS_VERROUILLES:
        raise TontineVerrouilleeError()

    tour = _obtenir_tour(tontine, id_tour)
    cotisation = next((c for c in tour.cotisations if c.id_membre == id_membre), None)
    if cotisation is None:
        raise CotisationIntrouvableError()

    cotisation.est_versee = est_versee
    cotisation.date_versement = datetime.utcnow() if est_versee else None
    db.commit()
    db.refresh(tontine)
    return tontine


def cloturer_tour(db: Session, id_client: int, id_tontine: int, id_tour: int) -> Tontine:
    """
    Clôture le tour EN_COURS une fois toutes les cotisations versées et
    active le tour suivant. S'il n'y a plus de tour suivant, la rotation
    est complète : la tontine passe TERMINEE.
    """
    tontine = obtenir_tontine_du_client(db, id_tontine, id_client)
    if tontine is None:
        raise TontineIntrouvableError()
    if tontine.statut in STATUTS_VERROUILLES:
        raise TontineVerrouilleeError()

    tour = _obtenir_tour(tontine, id_tour)
    if tour.statut != "EN_COURS":
        raise TourNonActifError()
    if any(not c.est_versee for c in tour.cotisations):
        raise TourIncompletError()

    tour.statut = "TERMINE"

    tour_suivant = next((t for t in tontine.tours if t.numero == tour.numero + 1), None)
    if tour_suivant is not None:
        tour_suivant.statut = "EN_COURS"
    else:
        tontine.statut = "TERMINEE"

    db.commit()
    db.refresh(tontine)
    return tontine


def annuler_tontine(db: Session, id_client: int, id_tontine: int, request: Optional[Request] = None) -> Tontine:
    """Arrête définitivement une tontine (groupe dissous, erreur de saisie)
    — les tours/cotisations restent consultables tels quels, rien n'est
    supprimé. Tracé dans l'AuditLog."""
    tontine = obtenir_tontine_du_client(db, id_tontine, id_client)
    if tontine is None:
        raise TontineIntrouvableError()
    if tontine.statut in STATUTS_VERROUILLES:
        raise TontineVerrouilleeError()

    statut_avant = tontine.statut
    tontine.statut = "ANNULEE"
    db.commit()
    db.refresh(tontine)

    enregistrer_action(
        db,
        id_utilisateur=id_client,
        action="TONTINE_ANNULEE",
        ressource="Tontine",
        id_ressource=tontine.id_tontine,
        donnees_avant={"statut": statut_avant},
        donnees_apres={"statut": "ANNULEE"},
        request=request,
    )
    return tontine
