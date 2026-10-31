"""
Simulateur d'objectif d'épargne (feature "objectif projet" : effort mensuel
auto + courbe de projection) — voir epargne.service.simuler_objectif et
POST /epargne/simuler. La simulation ne crée ni objectif ni compte.
"""
from datetime import date
from decimal import Decimal

from app.modules.epargne.service import simuler_objectif
from app.modules.plans import service as plans_service
from tests.conftest import TestingSessionLocal, se_connecter

REF = date(2026, 6, 15)


# --- Niveau service (déterministe, sans HTTP ni palier) ---

def test_simulation_effort_mensuel_et_projection():
    resultat = simuler_objectif(
        montant_cible=Decimal("3000000"),
        date_echeance=date(2028, 6, 15),  # 24 mois après REF
        aujourdhui=REF,
    )
    assert resultat["nombre_mois"] == 24
    assert resultat["montant_mensuel_requis"] == Decimal("125000.00")
    assert len(resultat["projection"]) == 24
    # Premier point = mois prochain, dernier point = cible exacte à l'échéance.
    assert resultat["projection"][0]["mois"] == "2026-07"
    assert resultat["projection"][-1]["mois"] == "2028-06"
    assert resultat["projection"][-1]["montant_cumule"] == Decimal("3000000")


def test_simulation_tient_compte_du_montant_initial():
    resultat = simuler_objectif(
        montant_cible=Decimal("3000000"),
        date_echeance=date(2028, 6, 15),
        montant_initial=Decimal("600000"),
        aujourdhui=REF,
    )
    # Reste 2 400 000 sur 24 mois -> 100 000/mois.
    assert resultat["montant_mensuel_requis"] == Decimal("100000.00")


def test_simulation_sans_echeance_pas_d_effort_mensuel():
    resultat = simuler_objectif(montant_cible=Decimal("500000"), date_echeance=None, aujourdhui=REF)
    assert resultat["nombre_mois"] is None
    assert resultat["montant_mensuel_requis"] is None
    assert resultat["projection"] == []


# --- Niveau API (palier ESSENTIEL requis, et aucun effet de bord) ---

def _upgrader_plan(id_client, nom_plan):
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email="epargne.simu@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": "motdepasse123",
            "first_name": "Simu",
            "last_name": "Epargne",
            "phone": "+237600000000",
        },
    )
    token = se_connecter(client, email, "motdepasse123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "ESSENTIEL")
    return headers


def test_endpoint_simuler_ne_cree_rien(client):
    headers = _register_and_login(client)

    reponse = client.post(
        "/api/v1/epargne/simuler",
        json={"montant_cible": 3000000, "date_echeance": "2030-12-31"},
        headers=headers,
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert Decimal(str(corps["montant_mensuel_requis"])) > 0
    assert len(corps["projection"]) >= 1
    assert Decimal(str(corps["projection"][-1]["montant_cumule"])) == Decimal("3000000")

    # Aucun objectif ni compte épargne ne doit avoir été créé par la simulation.
    assert client.get("/api/v1/epargne", headers=headers).json() == []
