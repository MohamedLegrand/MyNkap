import os
from datetime import date, timedelta

from app.modules.plans import service as plans_service
from app.modules.rapports import service as rapports_service
from app.modules.rapports.models import Rapport
from tests.conftest import TestingSessionLocal


def _upgrader_plan(id_client, nom_plan):
    """Passe directement par le service (jamais par HR-Skills Pay) — même
    principe que dans les autres fichiers de test."""
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email="rapports.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Rapport",
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


def _creer_compte(client, headers, solde_initial=100000):
    return client.post(
        "/api/v1/comptes",
        json={"nom": "Compte principal", "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


PERIODE_DEBUT = date(2026, 3, 1)
PERIODE_FIN = date(2026, 3, 31)


def test_demander_rapport_gratuit_ne_necessite_aucun_palier(client):
    headers = _register_and_login(client, "rapports.gratuit@example.com")

    reponse = client.post(
        "/api/v1/rapports",
        json={
            "type": "RELEVE_TRANSACTIONS",
            "periode_debut": PERIODE_DEBUT.isoformat(),
            "periode_fin": PERIODE_FIN.isoformat(),
        },
        headers=headers,
    )
    assert reponse.status_code == 201
    assert reponse.json()["statut"] == "EN_COURS"

    reponse2 = client.post(
        "/api/v1/rapports",
        json={
            "type": "BILAN_BUDGETAIRE",
            "periode_debut": PERIODE_DEBUT.isoformat(),
            "periode_fin": PERIODE_FIN.isoformat(),
        },
        headers=headers,
    )
    assert reponse2.status_code == 201


def test_demander_rapport_gate_par_palier(client):
    headers = _register_and_login(client, "rapports.gate@example.com")

    for type_rapport in ("DETTES_EPARGNE", "BILAN_FINANCIER", "PREDICTIONS"):
        reponse = client.post(
            "/api/v1/rapports",
            json={
                "type": type_rapport,
                "periode_debut": PERIODE_DEBUT.isoformat(),
                "periode_fin": PERIODE_FIN.isoformat(),
            },
            headers=headers,
        )
        assert reponse.status_code == 403, type_rapport


def test_demander_rapport_type_invalide_renvoie_422(client):
    headers = _register_and_login(client, "rapports.typeinvalide@example.com")
    reponse = client.post(
        "/api/v1/rapports",
        json={"type": "NIMPORTEQUOI", "periode_debut": "2026-03-01", "periode_fin": "2026-03-31"},
        headers=headers,
    )
    assert reponse.status_code == 422


def test_generer_rapport_releve_transactions_produit_un_pdf_valide(client, db_session):
    headers = _register_and_login(client, "rapports.releve@example.com")
    compte = _creer_compte(client, headers)
    categorie = next(c for c in client.get("/api/v1/categories", headers=headers).json() if c["nom"] == "Alimentation")

    client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"], "id_categorie": categorie["id_categorie"],
            "montant": 15000, "type": "DEPENSE", "date": PERIODE_DEBUT.isoformat(),
        },
        headers=headers,
    )

    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    rapport = rapports_service.demander_rapport(db_session, id_client, "RELEVE_TRANSACTIONS", PERIODE_DEBUT, PERIODE_FIN)
    rapport = rapports_service.generer_rapport(db_session, rapport.id_rapport)

    assert rapport.statut == "GENERE"
    assert rapport.chemin_fichier is not None
    assert os.path.exists(rapport.chemin_fichier)
    assert rapport.taille > 0

    with open(rapport.chemin_fichier, "rb") as f:
        contenu = f.read()
    assert contenu.startswith(b"%PDF")

    os.remove(rapport.chemin_fichier)


def test_generer_rapport_avec_donnees_en_erreur_marque_erreur(client, db_session, monkeypatch):
    headers = _register_and_login(client, "rapports.erreur@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]

    def echec(*args, **kwargs):
        raise RuntimeError("panne simulée")

    monkeypatch.setitem(rapports_service.CATALOGUE_RAPPORTS["RELEVE_TRANSACTIONS"], "donnees", echec)

    rapport = rapports_service.demander_rapport(db_session, id_client, "RELEVE_TRANSACTIONS", PERIODE_DEBUT, PERIODE_FIN)
    rapport = rapports_service.generer_rapport(db_session, rapport.id_rapport)

    assert rapport.statut == "ERREUR"
    assert rapport.chemin_fichier is None


def test_telecharger_rapport_non_pret_renvoie_409(client):
    headers = _register_and_login(client, "rapports.nonpret@example.com")
    rapport = client.post(
        "/api/v1/rapports",
        json={
            "type": "BILAN_BUDGETAIRE",
            "periode_debut": PERIODE_DEBUT.isoformat(),
            "periode_fin": PERIODE_FIN.isoformat(),
        },
        headers=headers,
    ).json()

    reponse = client.get(f"/api/v1/rapports/{rapport['id_rapport']}/telecharger", headers=headers)
    assert reponse.status_code == 409


def test_telecharger_rapport_genere_renvoie_le_fichier(client, db_session):
    headers = _register_and_login(client, "rapports.telecharger@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]

    rapport = rapports_service.demander_rapport(db_session, id_client, "BILAN_BUDGETAIRE", PERIODE_DEBUT, PERIODE_FIN)
    rapport = rapports_service.generer_rapport(db_session, rapport.id_rapport)
    assert rapport.statut == "GENERE"

    reponse = client.get(f"/api/v1/rapports/{rapport.id_rapport}/telecharger", headers=headers)
    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "application/pdf"
    assert reponse.content.startswith(b"%PDF")

    os.remove(rapport.chemin_fichier)


def test_obtenir_rapport_dun_autre_client_renvoie_404(client):
    headers_a = _register_and_login(client, "rapports.a@example.com")
    headers_b = _register_and_login(client, "rapports.b@example.com")

    rapport = client.post(
        "/api/v1/rapports",
        json={
            "type": "RELEVE_TRANSACTIONS",
            "periode_debut": PERIODE_DEBUT.isoformat(),
            "periode_fin": PERIODE_FIN.isoformat(),
        },
        headers=headers_a,
    ).json()

    reponse = client.get(f"/api/v1/rapports/{rapport['id_rapport']}", headers=headers_b)
    assert reponse.status_code == 404


def test_lister_rapports(client):
    headers = _register_and_login(client, "rapports.liste@example.com")
    client.post(
        "/api/v1/rapports",
        json={
            "type": "RELEVE_TRANSACTIONS",
            "periode_debut": PERIODE_DEBUT.isoformat(),
            "periode_fin": PERIODE_FIN.isoformat(),
        },
        headers=headers,
    )
    client.post(
        "/api/v1/rapports",
        json={
            "type": "BILAN_BUDGETAIRE",
            "periode_debut": PERIODE_DEBUT.isoformat(),
            "periode_fin": PERIODE_FIN.isoformat(),
        },
        headers=headers,
    )

    liste = client.get("/api/v1/rapports", headers=headers).json()
    assert len(liste) == 2


def test_generer_rapport_dettes_epargne_et_bilan_financier_et_predictions(client, db_session):
    """Vérifie que les 3 types gatés se génèrent aussi sans erreur, avec un
    client réellement sur le bon palier."""
    headers = _register_and_login(client, "rapports.premium@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "PREMIUM")

    for type_rapport in ("DETTES_EPARGNE", "BILAN_FINANCIER", "PREDICTIONS"):
        rapport = rapports_service.demander_rapport(db_session, id_client, type_rapport, PERIODE_DEBUT, PERIODE_FIN)
        rapport = rapports_service.generer_rapport(db_session, rapport.id_rapport)
        assert rapport.statut == "GENERE", type_rapport
        assert os.path.exists(rapport.chemin_fichier)
        os.remove(rapport.chemin_fichier)
