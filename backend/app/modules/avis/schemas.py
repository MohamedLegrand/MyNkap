from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CreerAvisRequest(BaseModel):
    note: int = Field(..., ge=1, le=5)
    commentaire: str = Field(..., min_length=1, max_length=1000)


class AvisOut(BaseModel):
    """Mon propre avis (client authentifié) — inclut le statut de
    modération, pour que le client sache où en est sa soumission."""
    id_avis: int
    note: int
    commentaire: str
    statut: str
    date_creation: datetime
    date_moderation: Optional[datetime]

    class Config:
        from_attributes = True


class AvisPublicOut(BaseModel):
    """Avis publié, affiché sur la landing page — jamais l'email ni le nom
    complet du client, seulement prénom + initiale du nom."""
    note: int
    commentaire: str
    auteur: str
    date_creation: datetime


class InvitationAvisOut(BaseModel):
    """Faut-il proposer activement (modale automatique) de laisser un avis
    maintenant ? Voir avis.service.doit_demander_avis."""
    demander: bool
