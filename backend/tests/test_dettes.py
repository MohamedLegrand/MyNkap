from decimal import Decimal

from app.modules.plans import service as plans_service
from tests.conftest import TestingSessionLocal


def _upgrader_plan(id_client, nom_plan):
    """
    Passe directement par le service (jamais par HR-Skills Pay) pour
    mettre le client de test sur le palier requis — la contrainte
    StaticPool fait que cette session partage la même connexion SQLite
    que celle utilisée par l'app, donc le changement est immédiatement
    visible.
    """
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email="dettes.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Dette",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "mot_de_passe": mot_de_passe},
    )
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Dettes & Créances est réservé au palier ESSENTIEL et plus (voir
    # module Plans/Abonnement) — un client GRATUIT recevrait 403 partout ici.
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "ESSENTIEL")
    return headers


def _creer_compte(client, headers, solde_initial=10000, nom="Compte"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def _solde(client, headers, id_compte):
    return Decimal(client.get(f"/api/v1/comptes/{id_compte}", headers=headers).json()["solde"])


def _patrimoine_net(client, headers):
    return Decimal(client.get("/api/v1/comptes/principal", headers=headers).json()["patrimoine_net"])


def test_creer_dette_credite_le_compte_mais_ne_change_pas_le_patrimoine_net(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    patrimoine_avant = _patrimoine_net(client, headers)

    reponse = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "DETTE", "nom": "Prêt Paul", "montant_total": 5000, "personne_impliquee": "Paul"},
        headers=headers,
    )

    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "EN_COURS"
    assert Decimal(body["montant_restant"]) == 5000
    assert Decimal(body["impact_patrimoine_net"]) == -5000  # passif

    assert _solde(client, headers, compte["id_compte"]) == 15000  # crédité
    assert _patrimoine_net(client, headers) == patrimoine_avant  # neutre : +cash, +passif


def test_creer_creance_debite_le_compte_mais_ne_change_pas_le_patrimoine_net(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    patrimoine_avant = _patrimoine_net(client, headers)

    reponse = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Prêt à Jean", "montant_total": 3000, "personne_impliquee": "Jean"},
        headers=headers,
    )

    assert reponse.status_code == 201
    body = reponse.json()
    assert Decimal(body["impact_patrimoine_net"]) == 3000  # actif

    assert _solde(client, headers, compte["id_compte"]) == 7000  # débité
    assert _patrimoine_net(client, headers) == patrimoine_avant  # neutre : -cash, +créance


def test_creance_refusee_si_solde_insuffisant(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=100)

    reponse = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Trop gros prêt", "montant_total": 5000},
        headers=headers,
    )

    assert reponse.status_code == 400
    assert _solde(client, headers, compte["id_compte"]) == 100  # inchangé


def test_rembourser_partiellement_puis_totalement_une_dette(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    dette = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "DETTE", "nom": "Prêt", "montant_total": 5000},
        headers=headers,
    ).json()
    # Solde après création : 15000 (crédité par la dette reçue)

    remb_partiel = client.post(
        f"/api/v1/dettes/{dette['id_dette']}/rembourser",
        json={"montant": 2000, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert remb_partiel.status_code == 200
    body = remb_partiel.json()
    assert body["statut"] == "PARTIELLEMENT_REMBOURSE"
    assert Decimal(body["montant_rembourse"]) == 2000
    assert Decimal(body["montant_restant"]) == 3000
    assert _solde(client, headers, compte["id_compte"]) == 13000  # 15000 - 2000

    remb_total = client.post(
        f"/api/v1/dettes/{dette['id_dette']}/rembourser",
        json={"montant": 3000, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert remb_total.status_code == 200
    body = remb_total.json()
    assert body["statut"] == "SOLDE"
    assert Decimal(body["montant_restant"]) == 0
    assert _solde(client, headers, compte["id_compte"]) == 10000  # revenu au solde initial


def test_dette_soldee_refuse_toute_nouvelle_operation(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    dette = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "DETTE", "nom": "Prêt", "montant_total": 1000},
        headers=headers,
    ).json()

    client.post(
        f"/api/v1/dettes/{dette['id_dette']}/rembourser",
        json={"montant": 1000, "id_compte": compte["id_compte"]},
        headers=headers,
    )

    reponse = client.post(
        f"/api/v1/dettes/{dette['id_dette']}/rembourser",
        json={"montant": 1, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_rembourser_une_creance_est_refuse(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    creance = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Prêté à Jean", "montant_total": 1000},
        headers=headers,
    ).json()

    reponse = client.post(
        f"/api/v1/dettes/{creance['id_dette']}/rembourser",
        json={"montant": 500, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_montant_superieur_au_restant_est_refuse(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    dette = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "DETTE", "nom": "Prêt", "montant_total": 1000},
        headers=headers,
    ).json()

    reponse = client.post(
        f"/api/v1/dettes/{dette['id_dette']}/rembourser",
        json={"montant": 5000, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_encaisser_une_creance_credite_le_compte_et_solde(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    creance = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Prêté à Jean", "montant_total": 3000},
        headers=headers,
    ).json()
    # Solde après création : 7000 (débité par la créance accordée)

    reponse = client.post(
        f"/api/v1/dettes/{creance['id_dette']}/encaisser",
        json={"montant": 3000, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 200
    body = reponse.json()
    assert body["statut"] == "SOLDE"
    assert _solde(client, headers, compte["id_compte"]) == 10000  # revenu au solde initial


def test_marquer_perte_reduit_le_patrimoine_net_et_verrouille(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    creance = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Prêté à Jean", "montant_total": 3000},
        headers=headers,
    ).json()

    patrimoine_avant_perte = _patrimoine_net(client, headers)

    reponse = client.post(f"/api/v1/dettes/{creance['id_dette']}/marquer-perte", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "PERTE"
    assert Decimal(reponse.json()["impact_patrimoine_net"]) == 0

    # La créance ne compte plus comme actif : le patrimoine net chute du
    # montant qui restait dû (3000, jamais remboursé).
    assert _patrimoine_net(client, headers) == patrimoine_avant_perte - 3000

    # Verrouillée : plus aucune opération possible.
    encaissement_refuse = client.post(
        f"/api/v1/dettes/{creance['id_dette']}/encaisser",
        json={"montant": 100, "id_compte": compte["id_compte"]},
        headers=headers,
    )
    assert encaissement_refuse.status_code == 400


def test_marquer_perte_sur_une_dette_est_refuse(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    dette = client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "DETTE", "nom": "Prêt", "montant_total": 1000},
        headers=headers,
    ).json()

    reponse = client.post(f"/api/v1/dettes/{dette['id_dette']}/marquer-perte", headers=headers)
    assert reponse.status_code == 400


def test_lister_dettes_filtre_par_type(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)

    client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "DETTE", "nom": "Prêt reçu", "montant_total": 1000},
        headers=headers,
    )
    client.post(
        "/api/v1/dettes",
        json={"id_compte": compte["id_compte"], "type": "CREANCE", "nom": "Prêté", "montant_total": 500},
        headers=headers,
    )

    toutes = client.get("/api/v1/dettes", headers=headers).json()
    assert len(toutes) == 2

    seulement_dettes = client.get("/api/v1/dettes?type=DETTE", headers=headers).json()
    assert len(seulement_dettes) == 1
    assert seulement_dettes[0]["type"] == "DETTE"
