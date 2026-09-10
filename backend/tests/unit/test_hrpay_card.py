"""
Tests unitaires purs (sans app, sans DB, sans réseau) pour la logique
locale du paiement carte : mapping des statuts E-NKAP vers les états
internes et « gross-up » de la commission carte.
"""
from decimal import Decimal

import pytest

from app.core import hrpay_card
from app.modules.plans import service as plans_service
from app.modules.recharges import service as recharges_service


@pytest.mark.parametrize(
    "statut_carte, attendu",
    [
        ("CAPTURED", "SUCCESS"),
        ("SETTLED", "SUCCESS"),
        ("FAILED", "FAILED"),
        ("CANCELED", "FAILED"),
        ("REFUNDED", "FAILED"),
        ("PENDING", "PENDING"),
        ("AUTHORIZED", "PENDING"),
        ("STATUT_INCONNU", "PENDING"),
    ],
)
def test_mapper_statut_carte(statut_carte, attendu):
    assert hrpay_card.mapper_statut(statut_carte) == attendu


@pytest.mark.parametrize(
    "montant, attendu",
    [
        (Decimal("10000"), Decimal("10363")),  # ceil(10000 / 0.965) = ceil(10362.69)
        (Decimal("2500"), Decimal("2591")),    # ceil(2500 / 0.965)  = ceil(2590.67)
        (Decimal("50000"), Decimal("51814")),  # ceil(50000 / 0.965) = ceil(51813.47)
        (Decimal("1"), Decimal("2")),          # ceil(1 / 0.965) = ceil(1.036) = 2
    ],
)
def test_gross_up_commission_carte(montant, attendu):
    # Les deux modules appliquent la même formule (duplication volontaire).
    assert recharges_service._montant_a_facturer_carte(montant) == attendu
    assert plans_service._montant_a_facturer_carte(montant) == attendu


def test_gross_up_couvre_toujours_le_montant_voulu():
    """Le net encaissé (montant_facturé × (1 − 3,5 %)) doit rester ≥ montant voulu."""
    taux = Decimal("0.035")
    for brut in (Decimal("100"), Decimal("999"), Decimal("10000"), Decimal("123456")):
        facture = recharges_service._montant_a_facturer_carte(brut)
        net = facture * (Decimal("1") - taux)
        assert net >= brut
