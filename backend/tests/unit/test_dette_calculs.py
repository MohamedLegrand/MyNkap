"""
Tests unitaires des méthodes pures du modèle Dette (backend/app/modules/
dettes/models.py) : aucun accès base de données, aucune requête — la Dette
est construite directement en mémoire avec les attributs nécessaires.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.modules.dettes.models import Dette


def _dette(**overrides) -> Dette:
    valeurs = {
        "type": "DETTE",
        "montant_total": Decimal("10000"),
        "montant_rembourse": Decimal("0"),
        "statut": "EN_COURS",
        "date_echeance": None,
    }
    valeurs.update(overrides)
    return Dette(**valeurs)


def test_montant_restant_diminue_avec_le_remboursement():
    dette = _dette(montant_total=Decimal("10000"), montant_rembourse=Decimal("4000"))
    assert dette.get_montant_restant() == Decimal("6000")


def test_pourcentage_rembourse_gere_le_montant_total_nul():
    dette = _dette(montant_total=Decimal("0"), montant_rembourse=Decimal("0"))
    assert dette.get_pourcentage_rembourse() == 0.0


def test_pourcentage_rembourse_calcule_correctement():
    dette = _dette(montant_total=Decimal("20000"), montant_rembourse=Decimal("5000"))
    assert dette.get_pourcentage_rembourse() == 25.0


def test_est_solde_reflete_le_statut():
    assert _dette(statut="SOLDE").est_solde() is True
    assert _dette(statut="EN_COURS").est_solde() is False


def test_marquer_comme_solde_change_le_statut():
    dette = _dette(statut="EN_COURS")
    dette.marquer_comme_solde()
    assert dette.statut == "SOLDE"


def test_jours_avant_echeance_none_sans_date():
    assert _dette(date_echeance=None).get_jours_avant_echeance() is None


def test_jours_avant_echeance_negatif_si_deja_depassee():
    dette = _dette(date_echeance=date.today() - timedelta(days=3))
    assert dette.get_jours_avant_echeance() == -3


def test_jours_avant_echeance_positif_si_a_venir():
    dette = _dette(date_echeance=date.today() + timedelta(days=5))
    assert dette.get_jours_avant_echeance() == 5


def test_impact_patrimoine_net_negatif_pour_une_dette():
    # Une dette qu'on doit est un passif : elle réduit le patrimoine net.
    dette = _dette(type="DETTE", montant_total=Decimal("10000"), montant_rembourse=Decimal("3000"), statut="EN_COURS")
    assert dette.get_impact_patrimoine_net() == Decimal("-7000")


def test_impact_patrimoine_net_positif_pour_une_creance():
    # Une créance à recevoir est un actif : elle augmente le patrimoine net.
    dette = _dette(type="CREANCE", montant_total=Decimal("10000"), montant_rembourse=Decimal("3000"), statut="EN_COURS")
    assert dette.get_impact_patrimoine_net() == Decimal("7000")


def test_impact_patrimoine_net_nul_pour_une_creance_perdue():
    # Une créance classée PERTE cesse de compter comme actif (voir
    # get_impact_patrimoine_net, principe 6.9).
    dette = _dette(type="CREANCE", montant_total=Decimal("10000"), montant_rembourse=Decimal("0"), statut="PERTE")
    assert dette.get_impact_patrimoine_net() == Decimal("0")
