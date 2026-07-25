from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.rapports import service
from app.modules.rapports.schemas import DemanderRapportRequest, RapportOut

router = APIRouter(prefix="/rapports", tags=["Rapports"])


@router.post("", response_model=RapportOut, status_code=status.HTTP_201_CREATED)
def demander_rapport(
    payload: DemanderRapportRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """
    Démarre la génération d'un rapport PDF. Renvoie immédiatement en
    EN_COURS — le fichier se construit en tâche de fond (voir
    worker.tasks.generer_rapport_tache). Interroger GET /rapports/{id}
    jusqu'à GENERE, puis /telecharger.
    """
    try:
        rapport = service.demander_rapport(db, client.id_client, payload.type, payload.periode_debut, payload.periode_fin)
    except service.TypeRapportInvalideError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type de rapport invalide.")
    except service.FonctionnaliteNonAutoriseeError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce type de rapport nécessite un palier supérieur.",
        )

    service.dispatcher_generation(rapport.id_rapport)
    return rapport


@router.get("", response_model=List[RapportOut])
def lister_rapports(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return service.lister_rapports(db, client.id_client)


@router.get("/{id_rapport}", response_model=RapportOut)
def obtenir_rapport(
    id_rapport: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    rapport = service.obtenir_rapport_du_client(db, id_rapport, client.id_client)
    if rapport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rapport introuvable.")
    return rapport


@router.get("/{id_rapport}/telecharger")
def telecharger_rapport(
    id_rapport: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    rapport = service.obtenir_rapport_du_client(db, id_rapport, client.id_client)
    if rapport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rapport introuvable.")
    if rapport.statut != "GENERE" or not rapport.chemin_fichier:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Le rapport n'est pas encore prêt.")

    nom_fichier = f"mynkap_{rapport.type.lower()}_{rapport.id_rapport}.pdf"
    return FileResponse(rapport.chemin_fichier, media_type="application/pdf", filename=nom_fichier)
