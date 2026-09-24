from slowapi import Limiter

from app.core.ip_client import obtenir_ip_reelle

# slowapi.util.get_remote_address lit request.client.host, qui derrière
# Nginx est l'adresse de Nginx lui-même (127.0.0.1) pour toutes les
# requêtes : la limite « par IP » se réduirait alors à une seule limite
# globale partagée par tous les clients. obtenir_ip_reelle (voir
# app.core.ip_client) résout la vraie IP amont, même logique que
# l'anti-fraude carte (plans/recharges).
limiter = Limiter(key_func=obtenir_ip_reelle)
