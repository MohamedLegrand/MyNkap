"""
Test d'intégration de bout en bout : un même client traverse plusieurs
modules (auth, plans, comptes, budgets, transactions, dettes, épargne,
analyse, jarvis) dans un seul parcours réaliste, via l'API HTTP comme le
ferait le frontend. Objectif : vérifier que les modules restent cohérents
ENSEMBLE (même client, même mois, mêmes données partagées) — chaque module
est déjà couvert isolément par ses propres tests unitaires dans tests/.
"""
from datetime import date
from decimal import Decimal

import app.modules.jarvis.service as jarvis_service
from app.modules.plans import service as plans_service
from tests.conftest import TestingSessionLocal, se_connecter


def _upgrader_plan(id_client, nom_plan):
    """Passe directement par le service (jamais par HR-Skills Pay) — même
    principe que dans tests/test_analyse.py et tests/test_jarvis.py."""
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def test_parcours_complet_budget_depasse_et_creance_perdue_remontent_partout(client, monkeypatch):
    # 1. Inscription + connexion + passage PREMIUM (Analyse et JARVIS sont
    # réservés à ce palier).
    email, mot_de_passe = "integration.parcours@example.com", "motdepasse123"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email, "mot_de_passe": mot_de_passe,
            "first_name": "Parcours", "last_name": "Complet", "phone": "+237600000000",
        },
    )
    headers = {"Authorization": f"Bearer {se_connecter(client, email, mot_de_passe).json()['access_token']}"}
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "PREMIUM")

    # 2. Compte + budget du mois en cours + une dépense qui le dépasse.
    compte = client.post(
        "/api/v1/comptes", json={"nom": "Cash", "type": "ESPECES", "solde_initial": 200000}, headers=headers,
    ).json()
    alimentation = next(
        c for c in client.get("/api/v1/categories", headers=headers).json() if c["nom"] == "Alimentation"
    )
    aujourdhui = date.today()
    client.post(
        "/api/v1/budgets",
        json={
            "id_categorie": alimentation["id_categorie"], "montant_limite": 1000,
            "mois": aujourdhui.month, "annee": aujourdhui.year,
        },
        headers=headers,
    )
    client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"], "id_categorie": alimentation["id_categorie"],
            "montant": 1500, "type": "DEPENSE", "date": aujourdhui.isoformat(),
        },
        headers=headers,
    )

    # 3. Une créance accordée jamais remboursée, constatée en perte.
    creance = client.post(
        "/api/v1/dettes",
        json={
            "id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Prêt à un cousin",
            "montant_total": 20000,
        },
        headers=headers,
    ).json()
    client.post(f"/api/v1/dettes/{creance['id_dette']}/marquer-perte", headers=headers)

    # 4. Un objectif d'épargne, pour vérifier qu'il traverse lui aussi tout
    # le parcours (compte dédié auto-créé, visible dans /comptes).
    client.post("/api/v1/epargne", json={"nom": "Fonds d'urgence", "montant_cible": 100000}, headers=headers)

    # --- Vérification 1 : le module Analyse voit le budget dépassé ET la créance perdue ensemble.
    resultats = client.get("/api/v1/analyse/COMPORTEMENT", headers=headers).json()["resultats"]
    assert resultats["budgets_depasses"] == 1
    assert resultats["creances_perdues"] == 1
    assert Decimal(resultats["montant_creances_perdues"]) == Decimal("20000")

    # --- Vérification 2 : l'objectif d'épargne a bien son compte dédié
    # (celui-ci est volontairement invisible dans GET /comptes par défaut
    # — voir comptes_service.lister_comptes — donc on vérifie via /epargne).
    objectifs = client.get("/api/v1/epargne", headers=headers).json()
    assert any(o["nom"] == "Fonds d'urgence" and o["id_compte_epargne"] for o in objectifs)

    # --- Vérification 3 : JARVIS voit la même réalité (contexte financier
    # partagé) — budget dépassé ET créance perdue apparaissent dans le
    # prompt injecté, sans que rien n'ait été répété manuellement ici.
    contexte_capture = {}

    def fausse_reponse(system_prompt, historique, question):
        contexte_capture["system_prompt"] = system_prompt
        return {
            "contenu": "Réponse", "necessite_clarification": False, "options_suggerees": None,
            "peut_se_permettre": None, "montant_suggere": None, "conseil_supplementaire": None, "actions": [],
        }

    monkeypatch.setattr(jarvis_service, "_appeler_groq", fausse_reponse)
    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "Comment se présente ma situation ce mois-ci ?"},
        headers=headers,
    )
    prompt = contexte_capture["system_prompt"]
    assert "Alimentation" in prompt
    assert "Prêt à un cousin" in prompt
    assert "constatées en perte" in prompt
    assert "Fonds d'urgence" in prompt
