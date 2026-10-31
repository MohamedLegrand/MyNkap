"""
Verrou virtuel de l'épargne projet : un retrait AVANT l'échéance sur un
objectif non atteint exige une confirmation explicite (voir
service.retirer / RetraitAnticipeNonConfirmeError → 409 RETRAIT_ANTICIPE).
Ce n'est pas un blocage dur : confirmé, le retrait passe.
"""
from app.modules.plans import service as plans_service
from tests.conftest import TestingSessionLocal, se_connecter

# Toujours dans le futur par rapport à la vie réelle du dépôt : garantit que
# l'échéance n'est pas encore passée quel que soit le jour d'exécution.
ECHEANCE_FUTURE = "2030-12-31"


def _upgrader_plan(id_client, nom_plan):
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": "motdepasse123",
            "first_name": "Verrou",
            "last_name": "Epargne",
            "phone": "+237600000000",
        },
    )
    token = se_connecter(client, email, "motdepasse123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "ESSENTIEL")
    return headers


def _compte(client, headers, solde_initial=100000):
    return client.post(
        "/api/v1/comptes",
        json={"nom": "Courant", "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def _objectif(client, headers, montant_cible=3000000, date_echeance=ECHEANCE_FUTURE):
    corps = {"nom": "Terrain Soa", "montant_cible": montant_cible}
    if date_echeance is not None:
        corps["date_echeance"] = date_echeance
    return client.post("/api/v1/epargne", json=corps, headers=headers).json()


def _alimenter(client, headers, id_objectif, compte, montant):
    return client.post(
        f"/api/v1/epargne/{id_objectif}/alimenter",
        json={"montant": montant, "id_compte_source": compte["id_compte"]},
        headers=headers,
    )


def test_retrait_anticipe_refuse_sans_confirmation(client):
    headers = _register_and_login(client, "verrou.refus@example.com")
    compte = _compte(client, headers)
    objectif = _objectif(client, headers)  # échéance lointaine, cible 3M non atteinte
    _alimenter(client, headers, objectif["id_objectif"], compte, 10000)

    reponse = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/retirer",
        json={"montant": 5000, "id_compte_destination": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 409
    detail = reponse.json()["detail"]
    assert detail["code"] == "RETRAIT_ANTICIPE"
    assert detail["mois_restants"] > 0


def test_retrait_anticipe_passe_si_confirme(client):
    headers = _register_and_login(client, "verrou.confirme@example.com")
    compte = _compte(client, headers)
    objectif = _objectif(client, headers)
    _alimenter(client, headers, objectif["id_objectif"], compte, 10000)

    reponse = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/retirer",
        json={
            "montant": 5000,
            "id_compte_destination": compte["id_compte"],
            "confirmer_retrait_anticipe": True,
        },
        headers=headers,
    )
    assert reponse.status_code == 200
    assert reponse.json()["montant_actuel"] == "5000.00"


def test_pas_de_verrou_sans_echeance(client):
    headers = _register_and_login(client, "verrou.sansecheance@example.com")
    compte = _compte(client, headers)
    objectif = _objectif(client, headers, date_echeance=None)  # pas d'échéance -> pas de verrou
    _alimenter(client, headers, objectif["id_objectif"], compte, 10000)

    reponse = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/retirer",
        json={"montant": 5000, "id_compte_destination": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 200
