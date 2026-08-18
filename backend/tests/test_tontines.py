from app.modules.plans import service as plans_service
from tests.conftest import TestingSessionLocal
from tests.conftest import se_connecter


def _upgrader_plan(id_client, nom_plan):
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email="tontine.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Tontine",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "ESSENTIEL")
    return headers


def _creer_tontine(client, headers, membres=None):
    membres = membres or [{"nom": "Awa"}, {"nom": "Biyick"}, {"nom": "Chantal"}]
    return client.post(
        "/api/v1/tontines",
        json={
            "nom": "Tontine du quartier",
            "montant_cotisation": 5000,
            "devise": "XAF",
            "frequence": "MENSUELLE",
            "date_debut": "2026-01-05",
            "membres": membres,
        },
        headers=headers,
    )


def test_creer_tontine_genere_la_rotation_complete(client):
    headers = _register_and_login(client)

    reponse = _creer_tontine(client, headers)
    assert reponse.status_code == 201
    data = reponse.json()

    assert data["nombre_membres"] == 3
    assert float(data["montant_total_par_tour"]) == 15000
    assert data["numero_tour_actuel"] == 1
    assert len(data["membres"]) == 3
    assert len(data["tours"]) == 3

    tour1 = next(t for t in data["tours"] if t["numero"] == 1)
    assert tour1["statut"] == "EN_COURS"
    assert tour1["nombre_cotisations_total"] == 3
    assert tour1["nombre_cotisations_versees"] == 0
    assert tour1["date_prevue"] == "2026-01-05"

    tour2 = next(t for t in data["tours"] if t["numero"] == 2)
    assert tour2["statut"] == "A_VENIR"
    assert tour2["date_prevue"] == "2026-02-05"

    tour3 = next(t for t in data["tours"] if t["numero"] == 3)
    assert tour3["date_prevue"] == "2026-03-05"


def test_creer_tontine_avec_moins_de_deux_membres_est_refuse(client):
    headers = _register_and_login(client)
    reponse = _creer_tontine(client, headers, membres=[{"nom": "Solo"}])
    assert reponse.status_code == 422


def test_marquer_cotisations_puis_cloturer_le_tour_active_le_suivant(client):
    headers = _register_and_login(client)
    tontine = _creer_tontine(client, headers).json()
    id_tontine = tontine["id_tontine"]
    tour1 = next(t for t in tontine["tours"] if t["numero"] == 1)
    membres = tontine["membres"]

    # Clôture refusée tant que toutes les cotisations ne sont pas versées.
    refus = client.post(f"/api/v1/tontines/{id_tontine}/tours/{tour1['id_tour']}/cloturer", headers=headers)
    assert refus.status_code == 400

    for m in membres:
        res = client.patch(
            f"/api/v1/tontines/{id_tontine}/tours/{tour1['id_tour']}/membres/{m['id_membre']}/cotisation",
            json={"est_versee": True},
            headers=headers,
        )
        assert res.status_code == 200

    cloture = client.post(f"/api/v1/tontines/{id_tontine}/tours/{tour1['id_tour']}/cloturer", headers=headers)
    assert cloture.status_code == 200
    data = cloture.json()

    tour1_apres = next(t for t in data["tours"] if t["numero"] == 1)
    assert tour1_apres["statut"] == "TERMINE"
    tour2_apres = next(t for t in data["tours"] if t["numero"] == 2)
    assert tour2_apres["statut"] == "EN_COURS"
    assert data["numero_tour_actuel"] == 2
    assert data["statut"] == "ACTIVE"


def test_cloturer_le_dernier_tour_termine_la_tontine(client):
    headers = _register_and_login(client)
    tontine = _creer_tontine(client, headers, membres=[{"nom": "Awa"}, {"nom": "Biyick"}]).json()
    id_tontine = tontine["id_tontine"]

    for tour in tontine["tours"]:
        for m in tontine["membres"]:
            client.patch(
                f"/api/v1/tontines/{id_tontine}/tours/{tour['id_tour']}/membres/{m['id_membre']}/cotisation",
                json={"est_versee": True},
                headers=headers,
            )

    tours = tontine["tours"]
    r1 = client.post(f"/api/v1/tontines/{id_tontine}/tours/{tours[0]['id_tour']}/cloturer", headers=headers)
    assert r1.status_code == 200
    assert r1.json()["statut"] == "ACTIVE"

    r2 = client.post(f"/api/v1/tontines/{id_tontine}/tours/{tours[1]['id_tour']}/cloturer", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["statut"] == "TERMINEE"
    assert r2.json()["numero_tour_actuel"] is None


def test_cloturer_un_tour_qui_nest_pas_en_cours_est_refuse(client):
    headers = _register_and_login(client)
    tontine = _creer_tontine(client, headers).json()
    id_tontine = tontine["id_tontine"]
    tour2 = next(t for t in tontine["tours"] if t["numero"] == 2)

    reponse = client.post(f"/api/v1/tontines/{id_tontine}/tours/{tour2['id_tour']}/cloturer", headers=headers)
    assert reponse.status_code == 400


def test_annuler_tontine_puis_toute_operation_est_refusee(client):
    headers = _register_and_login(client)
    tontine = _creer_tontine(client, headers).json()
    id_tontine = tontine["id_tontine"]
    tour1 = next(t for t in tontine["tours"] if t["numero"] == 1)
    membre = tontine["membres"][0]

    annulation = client.post(f"/api/v1/tontines/{id_tontine}/annuler", headers=headers)
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "ANNULEE"

    refus_cotisation = client.patch(
        f"/api/v1/tontines/{id_tontine}/tours/{tour1['id_tour']}/membres/{membre['id_membre']}/cotisation",
        json={"est_versee": True},
        headers=headers,
    )
    assert refus_cotisation.status_code == 400

    double_annulation = client.post(f"/api/v1/tontines/{id_tontine}/annuler", headers=headers)
    assert double_annulation.status_code == 400


def test_lister_et_obtenir_tontine(client):
    headers = _register_and_login(client)
    _creer_tontine(client, headers)

    liste = client.get("/api/v1/tontines", headers=headers)
    assert liste.status_code == 200
    assert len(liste.json()) == 1

    id_tontine = liste.json()[0]["id_tontine"]
    detail = client.get(f"/api/v1/tontines/{id_tontine}", headers=headers)
    assert detail.status_code == 200
    assert "membres" in detail.json()
    assert "tours" in detail.json()


def test_tontine_reservee_au_palier_essentiel(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "tontine.gratuit@example.com",
            "mot_de_passe": "motdepasse123",
            "first_name": "Gratuit",
            "last_name": "Test",
            "phone": "+237611111111",
        },
    )
    access_token = se_connecter(client, "tontine.gratuit@example.com", "motdepasse123").json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    # Nouvel inscrit = essai PREMIUM 30 jours (voir creer_abonnement_essai) :
    # il faut redescendre explicitement à GRATUIT pour tester le refus.
    _upgrader_plan(id_client, "GRATUIT")

    reponse = _creer_tontine(client, headers)
    assert reponse.status_code == 403
