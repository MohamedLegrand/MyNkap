from decimal import Decimal

from app.modules.transactions.models import Transaction
from tests.conftest import se_connecter


def _solde(client, headers, id_compte):
    return Decimal(client.get(f"/api/v1/comptes/{id_compte}", headers=headers).json()["solde"])


def _register_and_login(client, email="transactions.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Transaction",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _creer_compte(client, headers, solde_initial=100000, nom="Compte principal"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def _creer_categorie(db_session, id_client, nom="Catégorie Test", type_="DEPENSE"):
    # Nom distinct des catégories seedées par défaut à l'inscription (voir
    # budgets.service.CATEGORIES_PAR_DEFAUT), pour ne pas violer la
    # contrainte d'unicité (id_client, nom, type).
    from app.modules.budgets.models import Categorie

    categorie = Categorie(id_client=id_client, nom=nom, type=type_)
    db_session.add(categorie)
    db_session.commit()
    db_session.refresh(categorie)
    return categorie


def test_creer_depense_debite_le_compte(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    response = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 3000, "type": "DEPENSE"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["type"] == "DEPENSE"

    assert _solde(client, headers, compte["id_compte"]) == 7000


def test_depense_refusee_si_solde_insuffisant(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=1000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    response = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 5000, "type": "DEPENSE"},
        headers=headers,
    )

    assert response.status_code == 400
    assert _solde(client, headers, compte["id_compte"]) == 1000  # inchangé, la transaction n'a jamais été créée


def test_revenu_credite_le_compte(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=0)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client, nom="Revenu Test", type_="REVENU")

    response = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 200000, "type": "REVENU"},
        headers=headers,
    )

    assert response.status_code == 201
    assert _solde(client, headers, compte["id_compte"]) == 200000


def test_annuler_transaction_restaure_le_solde_et_ne_modifie_pas_loriginale(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    depense = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 3000, "type": "DEPENSE"},
        headers=headers,
    ).json()

    assert _solde(client, headers, compte["id_compte"]) == 7000

    annulation = client.post(f"/api/v1/transactions/{depense['id_transaction']}/annuler", headers=headers)
    assert annulation.status_code == 201
    assert annulation.json()["type"] == "ANNULATION"
    assert annulation.json()["id_transaction_annulee"] == depense["id_transaction"]

    assert _solde(client, headers, compte["id_compte"]) == 10000  # restauré

    originale = db_session.query(Transaction).filter(Transaction.id_transaction == depense["id_transaction"]).first()
    assert originale.type == "DEPENSE"  # jamais modifiée
    assert originale.montant == 3000


def test_annuler_deux_fois_la_meme_transaction_est_refuse(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    depense = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 3000, "type": "DEPENSE"},
        headers=headers,
    ).json()

    client.post(f"/api/v1/transactions/{depense['id_transaction']}/annuler", headers=headers)
    seconde_tentative = client.post(f"/api/v1/transactions/{depense['id_transaction']}/annuler", headers=headers)

    assert seconde_tentative.status_code == 400


def test_transaction_montant_inhabituel_est_marquee_suspecte(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=1000000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    # 3 dépenses "normales" pour établir une moyenne
    for _ in range(3):
        client.post(
            "/api/v1/transactions",
            json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 1000, "type": "DEPENSE"},
            headers=headers,
        )

    # Une dépense très supérieure à 3x la moyenne (1000) doit être signalée
    anormale = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 50000, "type": "DEPENSE"},
        headers=headers,
    ).json()

    assert anormale["est_suspecte"] is True


def test_annuler_suspicion_retombe_le_flag_et_trace_dans_laudit_log(client, db_session):
    from app.modules.audit.models import AuditLog

    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=1000000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    for _ in range(3):
        client.post(
            "/api/v1/transactions",
            json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 1000, "type": "DEPENSE"},
            headers=headers,
        )
    anormale = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 50000, "type": "DEPENSE"},
        headers=headers,
    ).json()
    assert anormale["est_suspecte"] is True

    reponse = client.post(f"/api/v1/transactions/{anormale['id_transaction']}/annuler-suspicion", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["est_suspecte"] is False

    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "LEVEE_SUSPICION", AuditLog.id_ressource == anormale["id_transaction"])
        .first()
    )
    assert audit is not None


def test_transfert_atomique_entre_deux_comptes(client):
    headers = _register_and_login(client)
    source = _creer_compte(client, headers, solde_initial=10000, nom="Source")
    destination = _creer_compte(client, headers, solde_initial=0, nom="Destination")

    response = client.post(
        "/api/v1/transferts",
        json={"id_compte_source": source["id_compte"], "id_compte_destination": destination["id_compte"], "montant": 4000},
        headers=headers,
    )

    assert response.status_code == 201

    assert _solde(client, headers, source["id_compte"]) == 6000
    assert _solde(client, headers, destination["id_compte"]) == 4000

    # Neutre sur le patrimoine net
    principal = client.get("/api/v1/comptes/principal", headers=headers).json()
    assert Decimal(principal["solde_total"]) == 10000


def test_transfert_refuse_si_solde_source_insuffisant(client):
    headers = _register_and_login(client)
    source = _creer_compte(client, headers, solde_initial=100, nom="Source")
    destination = _creer_compte(client, headers, solde_initial=0, nom="Destination")

    response = client.post(
        "/api/v1/transferts",
        json={"id_compte_source": source["id_compte"], "id_compte_destination": destination["id_compte"], "montant": 5000},
        headers=headers,
    )

    assert response.status_code == 400
    assert _solde(client, headers, destination["id_compte"]) == 0  # rien n'a été crédité


def test_reconcilier_recalcule_le_solde_depuis_lhistorique(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 3000, "type": "DEPENSE"},
        headers=headers,
    )

    # On corrompt volontairement le solde stocké pour vérifier que la
    # réconciliation le recalcule bien depuis l'historique réel.
    from app.modules.comptes.models import CompteFinancier

    compte_db = db_session.query(CompteFinancier).filter(CompteFinancier.id_compte == compte["id_compte"]).first()
    compte_db.solde = 999999
    db_session.commit()

    response = client.post(f"/api/v1/comptes/{compte['id_compte']}/reconcilier", headers=headers)
    assert response.status_code == 200
    assert Decimal(response.json()["solde"]) == 7000
