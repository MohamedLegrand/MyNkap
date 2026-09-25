from typing import Optional

from starlette.requests import Request

from app.core.config import settings


def obtenir_ip_reelle(request: Request) -> Optional[str]:
    """
    IP réelle du client final derrière la chaîne de proxys
    (HAProxy → Nginx → uvicorn, voir le guide de déploiement) —
    request.client.host serait celle de Nginx (127.0.0.1), pas celle du
    client, donc inutilisable telle quelle pour l'anti-fraude carte ou la
    limite de débit par IP.

    Le premier champ de X-Forwarded-For est celui qu'un client peut usurper
    lui-même : sans contrôle, n'importe qui peut envoyer une valeur
    différente à chaque requête et se faire passer pour une IP différente à
    chaque appel, annulant complètement la limite de débit par IP (confirmé
    exploitable en audit sur /auth/register, /auth/login, /auth/forgot-password
    et /auth/verify-otp). Cet en-tête n'est donc honoré que si la requête
    provient elle-même d'un proxy de confiance connu (TRUSTED_PROXY_IPS,
    typiquement Nginx sur le même hôte) ; sinon on retombe directement sur
    l'adresse TCP réelle du client, qu'il ne peut pas falsifier lui-même.
    Cela suppose que ce proxy de confiance écrase bien l'en-tête entrant
    avec l'adresse réelle du PROXY protocol reçue de HAProxy plutôt que de
    l'ajouter tel quel à un en-tête déjà présent — à vérifier côté
    configuration Nginx, hors de portée du code applicatif.
    """
    ip_directe = request.client.host if request.client else None
    transmis = request.headers.get("x-forwarded-for")
    if transmis and ip_directe in settings.trusted_proxy_ips_list:
        return transmis.split(",")[0].strip()
    return ip_directe
