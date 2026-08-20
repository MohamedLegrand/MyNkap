from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.avis.models import Avis
from app.modules.avis.schemas import AvisPublicOut
from app.modules.auth.models import Client


class AvisDejaExistantError(Exception):
    """Ce client a déjà soumis un avis — un seul par client, pas de resoumission."""


def creer_avis(db: Session, id_client: int, note: int, commentaire: str) -> Avis:
    if db.query(Avis).filter(Avis.id_client == id_client).first() is not None:
        raise AvisDejaExistantError()

    avis = Avis(id_client=id_client, note=note, commentaire=commentaire, statut="EN_ATTENTE")
    db.add(avis)
    db.commit()
    db.refresh(avis)
    return avis


def obtenir_mon_avis(db: Session, id_client: int) -> Optional[Avis]:
    return db.query(Avis).filter(Avis.id_client == id_client).first()


def lister_avis_publics(db: Session, limite: int = 12) -> List[AvisPublicOut]:
    """
    Avis publiés, les plus récents en premier — consultable sans
    authentification (voir router : GET /avis/publics, même tier que
    GET /plans). L'auteur est réduit à "Prénom N." : jamais l'email ni le
    nom complet d'un client sur une page publique.
    """
    resultats = (
        db.query(Avis, Client.first_name, Client.last_name)
        .join(Client, Avis.id_client == Client.id_client)
        .filter(Avis.statut == "PUBLIE")
        .order_by(Avis.date_moderation.desc())
        .limit(limite)
        .all()
    )
    return [
        AvisPublicOut(
            note=avis.note,
            commentaire=avis.commentaire,
            auteur=f"{first_name} {last_name[0].upper()}." if last_name else first_name,
            date_creation=avis.date_creation,
        )
        for avis, first_name, last_name in resultats
    ]
