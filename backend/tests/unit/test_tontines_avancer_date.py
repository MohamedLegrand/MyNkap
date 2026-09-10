"""
Test unitaire de la fonction pure tontines.service._avancer_date : calcule
la date du tour suivant selon la fréquence, sans aucun accès base de
données.
"""
from datetime import date

from app.modules.tontines.service import _avancer_date


def test_avancer_date_hebdomadaire_ajoute_sept_jours():
    assert _avancer_date(date(2026, 3, 5), "HEBDOMADAIRE") == date(2026, 3, 12)


def test_avancer_date_mensuelle_avance_dun_mois():
    assert _avancer_date(date(2026, 3, 15), "MENSUELLE") == date(2026, 4, 15)


def test_avancer_date_mensuelle_change_dannee_en_decembre():
    assert _avancer_date(date(2026, 12, 10), "MENSUELLE") == date(2027, 1, 10)


def test_avancer_date_mensuelle_plafonne_au_dernier_jour_du_mois_suivant():
    # Le 31 janvier n'existe pas en février -> ramené au dernier jour réel
    # (28 ou 29 selon l'année bissextile), jamais une exception ni un
    # débordement sur mars.
    assert _avancer_date(date(2026, 1, 31), "MENSUELLE") == date(2026, 2, 28)


def test_avancer_date_mensuelle_annee_bissextile():
    assert _avancer_date(date(2028, 1, 31), "MENSUELLE") == date(2028, 2, 29)
