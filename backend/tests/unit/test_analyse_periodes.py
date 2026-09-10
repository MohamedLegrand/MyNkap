"""
Tests unitaires des fonctions pures de calcul de périodes du module Analyse
(backend/app/modules/analyse/service.py) : aucun accès base de données.
"""
from datetime import date

from app.modules.analyse.service import _limites_mois, _mois_precedents, _mois_suivant


def test_limites_mois_mois_de_31_jours():
    assert _limites_mois(2026, 3) == (date(2026, 3, 1), date(2026, 3, 31))


def test_limites_mois_fevrier_annee_bissextile():
    assert _limites_mois(2028, 2) == (date(2028, 2, 1), date(2028, 2, 29))


def test_limites_mois_fevrier_annee_non_bissextile():
    assert _limites_mois(2026, 2) == (date(2026, 2, 1), date(2026, 2, 28))


def test_mois_precedents_renvoie_les_mois_pleins_avant_la_reference():
    # Référence : mars 2026 -> les 3 mois pleins précédents sont
    # février, janvier, décembre (de l'année précédente), dans cet ordre.
    resultat = _mois_precedents(date(2026, 3, 15), 3)
    assert resultat == [
        (date(2026, 2, 1), date(2026, 2, 28)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2025, 12, 1), date(2025, 12, 31)),
    ]


def test_mois_precedents_ne_renvoie_jamais_le_mois_de_reference():
    resultat = _mois_precedents(date(2026, 3, 15), 1)
    assert resultat == [(date(2026, 2, 1), date(2026, 2, 28))]


def test_mois_suivant_change_dannee_en_decembre():
    assert _mois_suivant(date(2026, 12, 10)) == (date(2027, 1, 1), date(2027, 1, 31))


def test_mois_suivant_cas_general():
    assert _mois_suivant(date(2026, 3, 10)) == (date(2026, 4, 1), date(2026, 4, 30))
