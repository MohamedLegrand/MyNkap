from typing import Optional

from starlette.requests import Request


def obtenir_ip_reelle(request: Request) -> Optional[str]:
    """
    IP réelle du client final derrière la chaîne de proxys
    (HAProxy → Nginx → uvicorn, voir le guide de déploiement) —
    request.client.host serait celle de Nginx (127.0.0.1), pas celle du
    client, donc inutilisable telle quelle pour l'anti-fraude carte ou la
    limite de débit par IP.

    Le premier champ de X-Forwarded-For est celui qu'un client peut usurper
    lui-même ; sa fiabilité dépend entièrement de la configuration du proxy
    en amont (Nginx doit écraser l'en-tête entrant avec l'adresse réelle
    du PROXY protocol reçue de HAProxy — jamais l'ajouter tel quel à un
    en-tête déjà présent). Cette fonction ne peut pas vérifier ça depuis le
    code applicatif ; elle centralise seulement la lecture, pour qu'un
    correctif éventuel de confiance dans la chaîne de proxys se fasse à un
    seul endroit plutôt que dans chaque module qui en avait besoin.
    """
    transmis = request.headers.get("x-forwarded-for")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.client.host if request.client else None
