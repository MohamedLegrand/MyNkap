from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.plans.dependencies import exiger_fonctionnalite
from app.modules.tontines import service
from app.modules.tontines.models import Tontine
from app.modules.tontines.schemas import (
    CotisationVersementUpdate,
    TontineCreate,
    TontineDetailOut,
    TontineOut,
)

router = APIRouter(
    prefix="/tontines",
    tags=["Tontines & Épargne Collective"],
    dependencies=[Depends(exiger_fonctionnalite("acces_tontine"))],
)


def _numero_tour_actuel(tontine: Tontine):
    tour_actif = next((t for t in tontine.tours if t.statut == "EN_COURS"), None)
    return tour_actif.numero if tour_actif else None


def _to_out(tontine: Tontine) -> TontineOut:
    return TontineOut(
        id_tontine=tontine.id_tontine,
        nom=tontine.nom,
        montant_cotisation=tontine.montant_cotisation,
        devise=tontine.devise,
        frequence=tontine.frequence,
        date_debut=tontine.date_debut,
        statut=tontine.statut,
        nombre_membres=len(tontine.membres),
        montant_total_par_tour=tontine.montant_cotisation * len(tontine.membres),
        numero_tour_actuel=_numero_tour_actuel(tontine),
        date_creation=tontine.date_creation,
    )


def _to_detail_out(tontine: Tontine) -> TontineDetailOut:
    base = _to_out(tontine)
    montant_total = tontine.montant_cotisation * len(tontine.membres)
    return TontineDetailOut(
        **base.model_dump(),
        membres=[
            {"id_membre": m.id_membre, "nom": m.nom, "telephone": m.telephone, "ordre": m.ordre}
            for m in tontine.membres
        ],
        tours=[
            {
                "id_tour": t.id_tour,
                "numero": t.numero,
                "id_membre_beneficiaire": t.id_membre_beneficiaire,
                "nom_beneficiaire": t.membre_beneficiaire.nom,
                "date_prevue": t.date_prevue,
                "statut": t.statut,
                "montant_total_attendu": montant_total,
                "nombre_cotisations_versees": sum(1 for c in t.cotisations if c.est_versee),
                "nombre_cotisations_total": len(t.cotisations),
                "cotisations": [
                    {
                        "id_cotisation": c.id_cotisation,
                        "id_membre": c.id_membre,
                        "nom_membre": c.membre.nom,
                        "est_versee": c.est_versee,
                        "date_versement": c.date_versement,
                    }
                    for c in t.cotisations
                ],
            }
            for t in tontine.tours
        ],
    )


@router.post("", response_model=TontineDetailOut, status_code=status.HTTP_201_CREATED)
def creer_tontine(
    payload: TontineCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Crée une tontine et génère automatiquement la rotation complète des
    tours (un par membre, dans l'ordre fourni) et les cotisations
    attendues à chaque tour."""
    tontine = service.creer_tontine(db, client.id_client, payload)
    return _to_detail_out(tontine)


@router.get("", response_model=List[TontineOut])
def lister_tontines(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return [_to_out(t) for t in service.lister_tontines(db, client.id_client)]


@router.get("/{id_tontine}", response_model=TontineDetailOut)
def obtenir_tontine(
    id_tontine: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    tontine = service.obtenir_tontine_du_client(db, id_tontine, client.id_client)
    if tontine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tontine introuvable")
    return _to_detail_out(tontine)


@router.patch("/{id_tontine}/tours/{id_tour}/membres/{id_membre}/cotisation", response_model=TontineDetailOut)
def marquer_cotisation(
    id_tontine: int,
    id_tour: int,
    id_membre: int,
    payload: CotisationVersementUpdate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Coche ou décoche manuellement le versement d'un membre pour un tour
    — reflète un paiement réel effectué hors de l'application."""
    try:
        tontine = service.marquer_cotisation(
            db, client.id_client, id_tontine, id_tour, id_membre, payload.est_versee
        )
    except service.TontineIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tontine introuvable")
    except service.TourIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour introuvable")
    except service.CotisationIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cotisation introuvable pour ce membre")
    except service.TontineVerrouilleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette tontine est terminée ou annulée"
        )
    return _to_detail_out(tontine)


@router.post("/{id_tontine}/tours/{id_tour}/cloturer", response_model=TontineDetailOut)
def cloturer_tour(
    id_tontine: int,
    id_tour: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Clôture le tour en cours (toutes les cotisations doivent être
    versées) et active le tour suivant, ou termine la tontine si c'était
    le dernier tour."""
    try:
        tontine = service.cloturer_tour(db, client.id_client, id_tontine, id_tour)
    except service.TontineIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tontine introuvable")
    except service.TourIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour introuvable")
    except service.TontineVerrouilleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette tontine est terminée ou annulée"
        )
    except service.TourNonActifError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Seul le tour en cours peut être clôturé"
        )
    except service.TourIncompletError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Toutes les cotisations de ce tour doivent être versées avant de le clôturer",
        )
    return _to_detail_out(tontine)


@router.post("/{id_tontine}/annuler", response_model=TontineOut)
def annuler_tontine(
    id_tontine: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Arrête définitivement une tontine (groupe dissous, erreur de
    saisie). Rien n'est supprimé : tours et cotisations restent
    consultables tels quels."""
    try:
        tontine = service.annuler_tontine(db, client.id_client, id_tontine)
    except service.TontineIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tontine introuvable")
    except service.TontineVerrouilleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette tontine est déjà terminée ou annulée"
        )
    return _to_out(tontine)
