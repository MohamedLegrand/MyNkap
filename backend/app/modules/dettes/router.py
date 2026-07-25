from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.dettes import service
from app.modules.dettes.models import Dette
from app.modules.dettes.schemas import DetteCreate, DetteOut, EncaisserRequest, RembourserRequest
from app.modules.plans.dependencies import exiger_fonctionnalite

router = APIRouter(
    prefix="/dettes",
    tags=["Dettes & Créances"],
    dependencies=[Depends(exiger_fonctionnalite("acces_dettes"))],
)


def _to_out(dette: Dette) -> DetteOut:
    return DetteOut(
        id_dette=dette.id_dette,
        id_compte=dette.id_compte,
        nom=dette.nom,
        type=dette.type,
        montant_total=dette.montant_total,
        montant_rembourse=dette.montant_rembourse,
        montant_restant=dette.get_montant_restant(),
        personne_impliquee=dette.personne_impliquee,
        date_echeance=dette.date_echeance,
        statut=dette.statut,
        jours_avant_echeance=dette.get_jours_avant_echeance(),
        impact_patrimoine_net=dette.get_impact_patrimoine_net(),
        date_creation=dette.date_creation,
        date_modification=dette.date_modification,
    )


@router.post("", response_model=DetteOut, status_code=status.HTTP_201_CREATED)
def creer_dette(
    payload: DetteCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Déclare une dette reçue ou une créance accordée. Génère une
    Transaction DETTE_RECUE/CREANCE_ACCORDEE traçant le mouvement de
    trésorerie associé."""
    try:
        dette = service.creer_dette(db, client.id_client, payload)
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.SoldeInsuffisantError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant pour accorder cette créance"
        )
    return _to_out(dette)


@router.get("", response_model=List[DetteOut])
def lister_dettes(
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return [_to_out(d) for d in service.lister_dettes(db, client.id_client, type)]


@router.get("/{id_dette}", response_model=DetteOut)
def obtenir_dette(
    id_dette: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    dette = service.obtenir_dette_du_client(db, id_dette, client.id_client)
    if dette is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dette introuvable")
    return _to_out(dette)


@router.post("/{id_dette}/rembourser", response_model=DetteOut)
def rembourser(
    id_dette: int,
    payload: RembourserRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Rembourse (partiellement ou totalement) une dette. Crée une
    Transaction REMBOURSEMENT_DETTE — montant_rembourse et statut sont
    recalculés depuis l'historique, jamais incrémentés directement."""
    try:
        dette = service.rembourser(db, client.id_client, id_dette, payload.montant, payload.id_compte)
    except service.DetteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dette introuvable")
    except service.TypeOperationIncompatibleError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette opération n'est valide que pour une dette (DETTE)"
        )
    except service.DetteVerrouilleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette dette est déjà soldée ou classée en perte"
        )
    except service.MontantSuperieurAuRestantError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le montant dépasse ce qu'il reste à rembourser"
        )
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    except service.SoldeInsuffisantError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solde insuffisant sur ce compte")
    return _to_out(dette)


@router.post("/{id_dette}/encaisser", response_model=DetteOut)
def encaisser(
    id_dette: int,
    payload: EncaisserRequest,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Encaisse (partiellement ou totalement) une créance. Crée une
    Transaction ENCAISSEMENT_CREANCE."""
    try:
        dette = service.encaisser(db, client.id_client, id_dette, payload.montant, payload.id_compte)
    except service.DetteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créance introuvable")
    except service.TypeOperationIncompatibleError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette opération n'est valide que pour une créance (CREANCE)",
        )
    except service.DetteVerrouilleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette créance est déjà soldée ou classée en perte"
        )
    except service.MontantSuperieurAuRestantError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le montant dépasse ce qu'il reste à encaisser"
        )
    except service.CompteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    return _to_out(dette)


@router.post("/{id_dette}/marquer-perte", response_model=DetteOut)
def marquer_comme_perte(
    id_dette: int,
    request: Request,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Constate qu'une créance est irrécouvrable (manuel, jamais
    automatique). Verrouille définitivement l'objet."""
    try:
        dette = service.marquer_comme_perte(db, client.id_client, id_dette, request=request)
    except service.DetteIntrouvableError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créance introuvable")
    except service.TypeOperationIncompatibleError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une créance peut être marquée en perte"
        )
    except service.DetteVerrouilleeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cette créance est déjà soldée ou classée en perte"
        )
    return _to_out(dette)
