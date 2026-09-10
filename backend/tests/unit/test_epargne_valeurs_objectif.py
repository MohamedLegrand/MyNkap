"""
Test unitaire de epargne.service.calculer_valeurs_objectif : construit un
ObjectifEpargne et son CompteFinancier dédié entièrement en mémoire (jamais
ajoutés à une session), sans aucun accès base de données.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.modules.comptes.models import CompteFinancier
from app.modules.epargne.models import ObjectifEpargne
from app.modules.epargne.service import calculer_valeurs_objectif


def _objectif(solde_actuel: Decimal, montant_cible: Decimal, date_echeance=None) -> ObjectifEpargne:
    compte = CompteFinancier(nom="Épargne test", type="EPARGNE", devise="XAF", solde=solde_actuel, est_actif=True)
    objectif = ObjectifEpargne(nom="Objectif test", montant_cible=montant_cible, date_echeance=date_echeance)
    objectif.compte_epargne = compte  # relation assignée directement, sans session
    return objectif


def test_montant_actuel_reprend_le_solde_du_compte_dedie():
    objectif = _objectif(Decimal("30000"), Decimal("100000"))
    valeurs = calculer_valeurs_objectif(objectif)
    assert valeurs["montant_actuel"] == Decimal("30000")
    assert valeurs["montant_restant"] == Decimal("70000")


def test_pourcentage_atteint_gere_la_cible_nulle():
    objectif = _objectif(Decimal("0"), Decimal("0"))
    valeurs = calculer_valeurs_objectif(objectif)
    assert valeurs["pourcentage_atteint"] == 0.0


def test_pourcentage_atteint_calcule_correctement():
    objectif = _objectif(Decimal("25000"), Decimal("100000"))
    valeurs = calculer_valeurs_objectif(objectif)
    assert valeurs["pourcentage_atteint"] == 25.0


def test_montant_mensuel_requis_none_sans_echeance():
    objectif = _objectif(Decimal("0"), Decimal("100000"), date_echeance=None)
    valeurs = calculer_valeurs_objectif(objectif)
    assert valeurs["montant_mensuel_requis"] is None


def test_montant_mensuel_requis_nul_si_objectif_deja_atteint():
    objectif = _objectif(Decimal("100000"), Decimal("100000"), date_echeance=date.today() + timedelta(days=60))
    valeurs = calculer_valeurs_objectif(objectif)
    assert valeurs["montant_mensuel_requis"] == Decimal("0")


def test_montant_mensuel_requis_reparti_sur_les_mois_restants():
    # Échéance dans exactement 2 mois civils : 60 000 restants / 2 mois = 30 000.
    aujourdhui = date.today()
    total_mois = aujourdhui.year * 12 + (aujourdhui.month - 1) + 2
    echeance = date(total_mois // 12, total_mois % 12 + 1, 1)
    objectif = _objectif(Decimal("40000"), Decimal("100000"), date_echeance=echeance)
    valeurs = calculer_valeurs_objectif(objectif)
    assert valeurs["montant_mensuel_requis"] == Decimal("30000")
