"""
Horodatage UTC — remplace datetime.utcnow()/utcfromtimestamp(), dépréciées
depuis Python 3.12 (retirées dans une future version). Renvoie des
datetimes NAÏFS (sans tzinfo) représentant l'heure UTC, pour un
comportement strictement identique à l'ancien datetime.utcnow() — toutes
les colonnes DateTime de ce projet sont naïves ; mélanger naïf et aware
lèverait TypeError à la première comparaison, donc on ne bascule jamais
vers des datetimes aware ici, seulement vers l'API non dépréciée.
"""
from datetime import datetime, timezone


def maintenant_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def depuis_timestamp_utc(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None)
