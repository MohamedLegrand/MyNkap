"""
Tests unitaires de la création d'un compte financier : validation du
schéma Pydantic (CompteFinancierCreate) et fonctions pures de crédit/débit
et de vérification de solde (backend/app/modules/comptes/). Aucun accès
base de données, aucun client HTTP.
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.comptes.models import CompteFinancier
from app.modules.comptes.schemas import CompteFinancierCreate
from app.modules.comptes.service import crediter_compte, debiter_compte   


# --- Validation du payload de création (CompteFinancierCreate) ---

def test_payload_valide_est_accepte_avec_ses_valeurs_par_defaut():
    payload = CompteFinancierCreate(nom="Mon compte Orange", type="MOBILE_MONEY")
    assert payload.devise == "XAF"
    assert payload.solde_initial == Decimal("0")


def test_payload_accepte_un_solde_initial_positif():
    payload = CompteFinancierCreate(nom="Cash", type="ESPECES", solde_initial=Decimal("50000"))
    assert payload.solde_initial == Decimal("50000")


def test_nom_vide_est_refuse():
    with pytest.raises(ValidationError):
        CompteFinancierCreate(nom="", type="ESPECES")


def test_type_hors_catalogue_est_refuse():
    with pytest.raises(ValidationError):
        CompteFinancierCreate(nom="Compte test", type="CRYPTO")


def test_devise_de_longueur_incorrecte_est_refusee():
    with pytest.raises(ValidationError):
        CompteFinancierCreate(nom="Compte test", type="ESPECES", devise="EU")


def test_solde_initial_negatif_est_refuse():
    with pytest.raises(ValidationError):
        CompteFinancierCreate(nom="Compte test", type="ESPECES", solde_initial=Decimal("-1"))


# --- Crédit / débit (fonctions pures, appelées uniquement sur un compte déjà verrouillé en base) ---

def test_crediter_compte_augmente_le_solde():
    compte = CompteFinancier(nom="Cash", type="ESPECES", solde=Decimal("1000"))
    crediter_compte(compte, Decimal("500"))
    assert compte.solde == Decimal("1500")


def test_debiter_compte_diminue_le_solde():
    compte = CompteFinancier(nom="Cash", type="ESPECES", solde=Decimal("1000"))
    debiter_compte(compte, Decimal("300"))
    assert compte.solde == Decimal("700")


def test_est_suffisant_vrai_si_le_solde_couvre_le_montant():
    compte = CompteFinancier(nom="Cash", type="ESPECES", solde=Decimal("1000"))
    assert compte.est_suffisant(Decimal("1000")) is True
    assert compte.est_suffisant(Decimal("999")) is True


def test_est_suffisant_faux_si_le_solde_ne_couvre_pas_le_montant():
    compte = CompteFinancier(nom="Cash", type="ESPECES", solde=Decimal("1000"))
    assert compte.est_suffisant(Decimal("1001")) is False
