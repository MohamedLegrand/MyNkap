from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.comptes import service
from app.modules.comptes.models import CompteFinancier
from app.modules.comptes.schemas import (
    CompteFinancierCreate,
    CompteFinancierUpdate,
    CompteFinancierOut,
    ComptePrincipalOut,
)

router = APIRouter(prefix="/comptes", tags=["Comptes financiers"])

EXTENSIONS_PAR_TYPE_LOGO = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
TAILLE_MAX_LOGO = 3 * 1024 * 1024  # 3 Mo


def _contenu_correspond_au_type_declare(contenu: bytes, content_type: str) -> bool:
    """Vérifie la signature binaire réelle : le Content-Type envoyé par le
    navigateur n'est qu'une déclaration, jamais une garantie (même contrôle
    que la photo de profil, voir auth.router — dupliqué volontairement,
    chaque module reste autonome). SVG volontairement exclu : il peut
    embarquer du script."""
    if content_type == "image/png":
        return contenu.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return contenu.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return contenu[:4] == b"RIFF" and contenu[8:12] == b"WEBP"
    return False


def _get_compte_ou_404(db: Session, id_compte: int, id_client: int) -> CompteFinancier:
    compte = service.obtenir_compte_du_client(db, id_compte, id_client)
    if compte is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")
    return compte


@router.post("", response_model=CompteFinancierOut, status_code=status.HTTP_201_CREATED)
def creer_compte(
    payload: CompteFinancierCreate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Créer un compte financier. Un solde_initial > 0 génère automatiquement
    une Transaction DEPOT_INITIAL tracée."""
    return service.creer_compte(db, client.id_client, payload)


@router.get("", response_model=List[CompteFinancierOut])
def lister_comptes(
    include_inactifs: bool = False,
    include_epargne_dediees: bool = False,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Liste les comptes financiers du client authentifié. Par défaut, ne
    renvoie que les comptes actifs, et exclut les comptes épargne dédiés à
    un objectif (consultables via /epargne)."""
    return service.lister_comptes(db, client.id_client, include_inactifs, include_epargne_dediees)


@router.get("/principal", response_model=ComptePrincipalOut)
def obtenir_compte_principal(
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Compte agrégateur en lecture seule : solde total des comptes actifs
    et patrimoine net (solde total - dettes + créances)."""
    compte_principal = service.synchroniser_compte_principal(db, client.id_client)
    patrimoine_net = service.calculer_patrimoine_net(db, client.id_client)
    return ComptePrincipalOut(
        id_compte_principal=compte_principal.id_compte_principal,
        solde_total=compte_principal.solde_total,
        devise=compte_principal.devise,
        patrimoine_net=patrimoine_net,
        date_mise_a_jour=compte_principal.date_mise_a_jour,
    )


@router.get("/{id_compte}", response_model=CompteFinancierOut)
def obtenir_compte(
    id_compte: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    return _get_compte_ou_404(db, id_compte, client.id_client)


@router.patch("/{id_compte}", response_model=CompteFinancierOut)
def modifier_compte(
    id_compte: int,
    payload: CompteFinancierUpdate,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Modifie le nom et/ou le type d'un compte. Le solde n'est jamais
    modifiable via cet endpoint (voir CompteFinancierUpdate)."""
    compte = _get_compte_ou_404(db, id_compte, client.id_client)
    return service.modifier_compte(db, compte, payload)


@router.post("/{id_compte}/logo", response_model=CompteFinancierOut)
async def importer_logo(
    id_compte: int,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Importe le logo personnalisé d'un compte (JPEG, PNG ou WebP, 3 Mo max)."""
    compte = _get_compte_ou_404(db, id_compte, client.id_client)

    extension = EXTENSIONS_PAR_TYPE_LOGO.get(logo.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non supporté (JPEG, PNG ou WebP uniquement).",
        )
    contenu = await logo.read()
    if len(contenu) > TAILLE_MAX_LOGO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le logo dépasse la taille maximale autorisée (3 Mo).",
        )
    if not _contenu_correspond_au_type_declare(contenu, logo.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier envoyé n'est pas une image valide du format annoncé.",
        )
    return service.enregistrer_logo_importe(db, compte, contenu, extension)


@router.delete("/{id_compte}/logo", response_model=CompteFinancierOut)
def retirer_logo(
    id_compte: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Retire le logo du compte (retour au logo par défaut du type, ou vide)."""
    compte = _get_compte_ou_404(db, id_compte, client.id_client)
    return service.retirer_logo(db, compte)


@router.delete("/{id_compte}", status_code=status.HTTP_204_NO_CONTENT)
def desactiver_compte(
    id_compte: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Désactivation logique (soft delete) — jamais de suppression réelle."""
    compte = _get_compte_ou_404(db, id_compte, client.id_client)
    service.desactiver_compte(db, compte)


@router.post("/{id_compte}/reactiver", response_model=CompteFinancierOut)
def reactiver_compte(
    id_compte: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    compte = _get_compte_ou_404(db, id_compte, client.id_client)
    return service.reactiver_compte(db, compte)


@router.post("/{id_compte}/reconcilier", response_model=CompteFinancierOut)
def reconcilier_compte(
    id_compte: int,
    db: Session = Depends(get_db),
    client: Client = Depends(get_current_active_client),
):
    """Recalcule le solde depuis la somme des impacts de toutes les
    transactions réelles du compte (module Transactions)."""
    compte = _get_compte_ou_404(db, id_compte, client.id_client)
    return service.reconcilier_compte(db, compte)
