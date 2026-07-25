from decimal import Decimal


def _register_and_login(client, email="epargne.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Epargne",
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
    # Épargne est réservé au palier ESSENTIEL et plus (voir module
    # Plans/Abonnement) — un client GRATUIT recevrait 403 partout ici.
    client.post(
        "/api/v1/abonnement/changer-plan",
        json={"nom_plan": "ESSENTIEL", "cycle_facturation": "MENSUEL"},
        headers=headers,
    )
    return headers


def _creer_compte(client, headers, solde_initial=100000, nom="Compte principal"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def test_creer_objectif_cree_un_compte_dedie_invisible(client):
    headers = _register_and_login(client)
    _creer_compte(client, headers, solde_initial=100000)

    reponse = client.post(
        "/api/v1/epargne",
        json={"nom": "Acheter une moto", "montant_cible": 500000, "date_echeance": "2026-12-31"},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["statut"] == "EN_COURS"
    assert Decimal(body["montant_actuel"]) == 0
    assert Decimal(body["montant_restant"]) == 500000

    # Le compte dédié existe bien...
    assert body["id_compte_epargne"] is not None

    # ...mais n'apparaît pas dans la liste générale des comptes
    comptes = client.get("/api/v1/comptes", headers=headers).json()
    ids_comptes = [c["id_compte"] for c in comptes]
    assert body["id_compte_epargne"] not in ids_comptes

    # Il redevient visible si explicitement demandé
    comptes_avec_epargne = client.get("/api/v1/comptes?include_epargne_dediees=true", headers=headers).json()
    ids_avec_epargne = [c["id_compte"] for c in comptes_avec_epargne]
    assert body["id_compte_epargne"] in ids_avec_epargne


def test_alimenter_est_un_transfert_neutre_sur_le_patrimoine_net(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=100000)
    patrimoine_avant = Decimal(client.get("/api/v1/comptes/principal", headers=headers).json()["patrimoine_net"])

    objectif = client.post(
        "/api/v1/epargne",
        json={"nom": "Moto", "montant_cible": 500000},
        headers=headers,
    ).json()

    reponse = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/alimenter",
        json={"montant": 50000, "id_compte_source": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 200
    body = reponse.json()
    assert Decimal(body["montant_actuel"]) == 50000
    assert body["statut"] == "EN_COURS"

    solde_compte = Decimal(client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"])
    assert solde_compte == 50000  # 100000 - 50000

    patrimoine_apres = Decimal(client.get("/api/v1/comptes/principal", headers=headers).json()["patrimoine_net"])
    assert patrimoine_apres == patrimoine_avant  # neutre : juste déplacé


def test_alimenter_refuse_si_solde_insuffisant(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=1000)
    objectif = client.post(
        "/api/v1/epargne", json={"nom": "Moto", "montant_cible": 500000}, headers=headers
    ).json()

    reponse = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/alimenter",
        json={"montant": 50000, "id_compte_source": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 400


def test_atteindre_objectif_puis_retirer_repasse_en_cours(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=100000)
    objectif = client.post(
        "/api/v1/epargne", json={"nom": "Petit objectif", "montant_cible": 10000}, headers=headers
    ).json()

    atteint = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/alimenter",
        json={"montant": 10000, "id_compte_source": compte["id_compte"]},
        headers=headers,
    ).json()
    assert atteint["statut"] == "ATTEINT"

    retrait = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/retirer",
        json={"montant": 4000, "id_compte_destination": compte["id_compte"]},
        headers=headers,
    ).json()
    assert retrait["statut"] == "EN_COURS"  # redescend, pas un verrou à sens unique
    assert Decimal(retrait["montant_actuel"]) == 6000


def test_abandonner_transfere_le_solde_et_verrouille(client):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=100000)
    autre_compte = _creer_compte(client, headers, solde_initial=0, nom="Autre compte")
    objectif = client.post(
        "/api/v1/epargne", json={"nom": "Moto", "montant_cible": 500000}, headers=headers
    ).json()

    client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/alimenter",
        json={"montant": 30000, "id_compte_source": compte["id_compte"]},
        headers=headers,
    )

    abandon = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/abandonner",
        json={"id_compte_destination": autre_compte["id_compte"]},
        headers=headers,
    )
    assert abandon.status_code == 200
    body = abandon.json()
    assert body["statut"] == "ABANDONNE"
    assert Decimal(body["montant_actuel"]) == 0

    # L'argent a bien été récupéré, rien n'est perdu
    solde_autre_compte = Decimal(
        client.get(f"/api/v1/comptes/{autre_compte['id_compte']}", headers=headers).json()["solde"]
    )
    assert solde_autre_compte == 30000

    # Le compte dédié est désactivé (visible seulement avec include_inactifs)
    comptes_actifs = client.get("/api/v1/comptes?include_epargne_dediees=true", headers=headers).json()
    assert body["id_compte_epargne"] not in [c["id_compte"] for c in comptes_actifs]

    # Verrouillé : plus aucune opération possible
    nouvelle_tentative = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/alimenter",
        json={"montant": 1000, "id_compte_source": compte["id_compte"]},
        headers=headers,
    )
    assert nouvelle_tentative.status_code == 400


def test_abandonner_sans_solde_ne_transfere_rien_mais_valide_le_compte_destination(client):
    headers = _register_and_login(client)
    objectif = client.post(
        "/api/v1/epargne", json={"nom": "Objectif vide", "montant_cible": 500000}, headers=headers
    ).json()

    # Compte destination inexistant : refusé même si rien à transférer
    reponse_invalide = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/abandonner",
        json={"id_compte_destination": 999999},
        headers=headers,
    )
    assert reponse_invalide.status_code == 404

    compte = _creer_compte(client, headers, solde_initial=0)
    reponse = client.post(
        f"/api/v1/epargne/{objectif['id_objectif']}/abandonner",
        json={"id_compte_destination": compte["id_compte"]},
        headers=headers,
    )
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "ABANDONNE"


def test_montant_mensuel_requis_sans_echeance_est_nul(client):
    headers = _register_and_login(client)
    objectif = client.post(
        "/api/v1/epargne", json={"nom": "Sans échéance", "montant_cible": 100000}, headers=headers
    ).json()
    assert objectif["montant_mensuel_requis"] is None


def test_objectif_dun_autre_client_renvoie_404(client):
    headers_a = _register_and_login(client, email="epargne.a@example.com")
    headers_b = _register_and_login(client, email="epargne.b@example.com")

    objectif = client.post(
        "/api/v1/epargne", json={"nom": "Privé", "montant_cible": 100000}, headers=headers_a
    ).json()

    reponse = client.get(f"/api/v1/epargne/{objectif['id_objectif']}", headers=headers_b)
    assert reponse.status_code == 404
