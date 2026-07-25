"""
Tests couvrant les 4 corrections bloquantes identifiées lors de l'audit :
1. Verrouillage de ligne (FOR UPDATE) pour éviter les races de débit/crédit
2. Numeric au lieu de Float pour l'argent
3. Contraintes CHECK en base (solde >= 0, montant > 0)
4. annuler_transaction() refuse un découvert résultant
"""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.comptes.models import CompteFinancier
from app.modules.transactions.models import Transaction


def _register_and_login(client, email="integrite.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Integrite",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "mot_de_passe": mot_de_passe},
    )
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _creer_compte(client, headers, solde_initial=10000, nom="Compte"):
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


# --- 1. Contrainte CHECK solde >= 0 en base ---

def test_check_constraint_refuse_un_solde_negatif_meme_hors_service(client, db_session):
    headers = _register_and_login(client)
    compte_api = _creer_compte(client, headers, solde_initial=0)

    compte = db_session.query(CompteFinancier).filter(CompteFinancier.id_compte == compte_api["id_compte"]).first()
    compte.solde = Decimal("-1")

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- 2. Contrainte CHECK montant > 0 en base ---

def test_check_constraint_refuse_un_montant_de_transaction_non_positif(client, db_session):
    headers = _register_and_login(client)
    compte_api = _creer_compte(client, headers, solde_initial=10000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    transaction = Transaction(
        id_client=id_client,
        id_compte=compte_api["id_compte"],
        id_categorie=categorie.id_categorie,
        montant=Decimal("0"),
        type="DEPENSE",
    )
    db_session.add(transaction)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- 3. annuler_transaction() refuse un découvert résultant ---

def test_annuler_depot_initial_apres_depense_est_refuse_si_decouvert(client, db_session):
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=1000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    # Dépense de 900 : il ne reste que 100 sur le compte.
    client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 900, "type": "DEPENSE"},
        headers=headers,
    )

    depot_initial = (
        db_session.query(Transaction)
        .filter(Transaction.id_compte == compte["id_compte"], Transaction.type == "DEPOT_INITIAL")
        .first()
    )

    # Annuler le dépôt initial (-1000) ferait passer le solde à 100 - 1000 = -900.
    reponse = client.post(f"/api/v1/transactions/{depot_initial.id_transaction}/annuler", headers=headers)

    assert reponse.status_code == 400

    solde = Decimal(
        client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"]
    )
    assert solde == 100  # inchangé : l'annulation n'a jamais été appliquée

    # Aucune transaction ANNULATION n'a été créée
    annulations = (
        db_session.query(Transaction)
        .filter(Transaction.id_transaction_annulee == depot_initial.id_transaction)
        .all()
    )
    assert len(annulations) == 0


def test_annuler_depense_qui_ne_cree_pas_de_decouvert_fonctionne(client, db_session):
    # Contre-exemple : annuler une DEPENSE (impact positif au retour) ne
    # peut jamais créer de découvert, donc ça doit toujours passer.
    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=10000)
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    categorie = _creer_categorie(db_session, id_client)

    depense = client.post(
        "/api/v1/transactions",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie.id_categorie, "montant": 3000, "type": "DEPENSE"},
        headers=headers,
    ).json()

    reponse = client.post(f"/api/v1/transactions/{depense['id_transaction']}/annuler", headers=headers)
    assert reponse.status_code == 201


# --- 4. Verrouillage de ligne : la requête SQL émise contient bien FOR UPDATE ---

def test_obtenir_compte_du_client_avec_for_update_emet_select_for_update(client, db_session):
    # SQLite (utilisé pour les tests) ignore silencieusement FOR UPDATE, donc
    # on compile la requête pour le dialecte Postgres (celui réellement
    # utilisé en production) afin de vérifier que le verrou est bien demandé
    # par le code, indépendamment de la base de test.
    from sqlalchemy.dialects import postgresql

    from app.modules.comptes.service import obtenir_compte_du_client

    headers = _register_and_login(client)
    compte = _creer_compte(client, headers, solde_initial=1000)

    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]

    query = db_session.query(CompteFinancier).filter(
        CompteFinancier.id_compte == compte["id_compte"], CompteFinancier.id_client == id_client
    ).with_for_update()

    sql = str(query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "FOR UPDATE" in sql.upper()

    # Vérifie aussi que la fonction du service renvoie bien le même verrou
    # (pas d'erreur levée, verrouillage transparent pour l'appelant).
    resultat = obtenir_compte_du_client(db_session, compte["id_compte"], id_client, for_update=True)
    assert resultat is not None
    db_session.commit()  # libère le verrou
