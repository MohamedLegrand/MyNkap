from decimal import Decimal

from app.modules.transactions.models import Transaction
from tests.conftest import se_connecter_avec_otp


def _register_and_login(client, email="comptes.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Compte",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter_avec_otp(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def test_creer_compte_sans_solde_initial(client):
    headers = _register_and_login(client)

    response = client.post(
        "/api/v1/comptes",
        json={"nom": "Orange Money", "type": "MOBILE_MONEY"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["solde"]) == 0
    assert body["est_actif"] is True
    assert body["devise"] == "XAF"


def test_creer_compte_avec_solde_initial_genere_une_transaction_depot_initial(client, db_session):
    headers = _register_and_login(client)

    response = client.post(
        "/api/v1/comptes",
        json={"nom": "Compte Bancaire", "type": "BANCAIRE", "solde_initial": 50000},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["solde"]) == 50000

    depots = (
        db_session.query(Transaction)
        .filter(Transaction.id_compte == body["id_compte"], Transaction.type == "DEPOT_INITIAL")
        .all()
    )
    assert len(depots) == 1
    assert depots[0].montant == 50000
    assert depots[0].id_categorie is None


def test_lister_comptes_exclut_les_inactifs_par_defaut(client):
    headers = _register_and_login(client)

    r1 = client.post("/api/v1/comptes", json={"nom": "Compte A", "type": "ESPECES"}, headers=headers)
    client.post("/api/v1/comptes", json={"nom": "Compte B", "type": "EPARGNE"}, headers=headers)

    id_compte_a = r1.json()["id_compte"]
    client.delete(f"/api/v1/comptes/{id_compte_a}", headers=headers)

    actifs = client.get("/api/v1/comptes", headers=headers).json()
    assert len(actifs) == 1
    assert actifs[0]["nom"] == "Compte B"

    tous = client.get("/api/v1/comptes?include_inactifs=true", headers=headers).json()
    assert len(tous) == 2


def test_obtenir_compte_dun_autre_client_renvoie_404(client):
    headers_a = _register_and_login(client, email="client.a@example.com")
    headers_b = _register_and_login(client, email="client.b@example.com")

    compte = client.post(
        "/api/v1/comptes", json={"nom": "Compte Privé", "type": "ESPECES"}, headers=headers_a
    ).json()

    response = client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers_b)
    assert response.status_code == 404


def test_modifier_compte_ignore_toute_tentative_de_changer_le_solde(client):
    headers = _register_and_login(client)
    compte = client.post(
        "/api/v1/comptes",
        json={"nom": "Compte", "type": "ESPECES", "solde_initial": 1000},
        headers=headers,
    ).json()

    response = client.patch(
        f"/api/v1/comptes/{compte['id_compte']}",
        json={"nom": "Nouveau nom", "solde": 999999},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nom"] == "Nouveau nom"
    assert Decimal(body["solde"]) == 1000  # inchangé malgré la tentative


def test_desactiver_puis_reactiver_compte(client):
    headers = _register_and_login(client)
    compte = client.post(
        "/api/v1/comptes", json={"nom": "Compte", "type": "ESPECES"}, headers=headers
    ).json()
    id_compte = compte["id_compte"]

    desactivation = client.delete(f"/api/v1/comptes/{id_compte}", headers=headers)
    assert desactivation.status_code == 204
    assert client.get(f"/api/v1/comptes/{id_compte}", headers=headers).json()["est_actif"] is False

    reactivation = client.post(f"/api/v1/comptes/{id_compte}/reactiver", headers=headers)
    assert reactivation.status_code == 200
    assert reactivation.json()["est_actif"] is True


def test_compte_principal_agrege_les_soldes_actifs_uniquement(client):
    headers = _register_and_login(client)
    compte_1 = client.post(
        "/api/v1/comptes", json={"nom": "Compte 1", "type": "ESPECES", "solde_initial": 10000}, headers=headers
    ).json()
    client.post(
        "/api/v1/comptes", json={"nom": "Compte 2", "type": "BANCAIRE", "solde_initial": 5000}, headers=headers
    )

    principal = client.get("/api/v1/comptes/principal", headers=headers).json()
    assert Decimal(principal["solde_total"]) == 15000
    assert Decimal(principal["patrimoine_net"]) == 15000

    client.delete(f"/api/v1/comptes/{compte_1['id_compte']}", headers=headers)

    principal_apres = client.get("/api/v1/comptes/principal", headers=headers).json()
    assert Decimal(principal_apres["solde_total"]) == 5000


def test_reconcilier_un_compte_sans_transaction_donne_un_solde_nul(client):
    # Cas simple ici ; le cas avec historique reel (recalcul depuis les
    # transactions) est couvert dans tests/test_transactions.py, qui depend
    # du module Transactions.
    headers = _register_and_login(client)
    compte = client.post(
        "/api/v1/comptes", json={"nom": "Compte", "type": "ESPECES"}, headers=headers
    ).json()

    response = client.post(f"/api/v1/comptes/{compte['id_compte']}/reconcilier", headers=headers)
    assert response.status_code == 200
    assert Decimal(response.json()["solde"]) == 0
