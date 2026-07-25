from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_active_client
from app.modules.auth.models import Client
from app.modules.plans import service as plans_service


def exiger_fonctionnalite(nom_attribut_acces: str):
    """
    Dependency FastAPI paramétrée : vérifie que le plan actif du client
    donne accès à la fonctionnalité demandée (ex. "acces_jarvis"). Ne
    s'applique qu'aux modules gérés par palier (Dettes, Épargne,
    Récurrentes, Templates, Analyse, JARVIS) — Comptes/Transactions/
    Budgets/Catégories restent gratuits pour tous, sans cette dependency.
    """
    def dependency(
        client: Client = Depends(get_current_active_client),
        db: Session = Depends(get_db),
    ) -> Client:
        abonnement = plans_service.obtenir_abonnement_actif(db, client.id_client)
        if not getattr(abonnement.plan, nom_attribut_acces, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cette fonctionnalité nécessite un palier supérieur.",
            )
        return client

    return dependency
