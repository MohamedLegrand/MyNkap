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

    Le contenu de X-Forwarded-For est celui qu'un client peut usurper
    lui-même : sans contrôle, n'importe qui peut envoyer une valeur
    différente à chaque requête et se faire passer pour une IP différente à
    chaque appel, annulant complètement la limite de débit par IP (confirmé
    exploitable en audit sur /auth/register, /auth/login, /auth/forgot-password
    et /auth/verify-otp). Cet en-tête n'est donc honoré que si la requête
    provient elle-même d'un proxy de confiance connu (TRUSTED_PROXY_IPS,
    typiquement Nginx sur le même hôte) ; sinon on retombe directement sur
    l'adresse TCP réelle du client, qu'il ne peut pas falsifier lui-même.

    Quand il est honoré, c'est le DERNIER champ de la liste qui est retenu,
    jamais le premier. Un proxy respectueux de la norme (RFC 7239) AJOUTE
    l'adresse de son émetteur direct à la fin de la valeur déjà présente —
    il ne l'écrase que s'il est explicitement configuré pour ça
    (`proxy_set_header X-Forwarded-For $realip_remote_addr;` côté Nginx,
    plutôt que `$proxy_add_x_forwarded_for`). Si le proxy de confiance est
    en mode "ajout" plutôt que "écrasement", un attaquant qui envoie lui-même
    `X-Forwarded-For: 1.2.3.4` verrait ce fournisseur y ajouter sa propre IP
    à la suite (`1.2.3.4, <IP réelle de l'attaquant>`) : prendre le premier
    champ redonnerait alors la main à l'attaquant malgré le filtre
    TRUSTED_PROXY_IPS ci-dessus. Le dernier champ, lui, est toujours celui
    que le proxy de confiance a lui-même constaté sur sa connexion TCP
    entrante — invérifiable par le code applicatif, mais jamais falsifiable
    par le client final, que l'en-tête soit écrasé ou complété.
    """
    ip_directe = request.client.host if request.client else None
    transmis = request.headers.get("x-forwarded-for")
    if transmis and ip_directe in settings.trusted_proxy_ips_list:
        champs = [ip.strip() for ip in transmis.split(",") if ip.strip()]
        if champs:
            return champs[-1]
    return ip_directe
