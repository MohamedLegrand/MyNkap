"""
Alertes proactives de rupture de solde (volet "conseiller proactif" de
JARVIS) — voir analyse.service.projeter_rupture_solde /
notifier_ruptures_solde_proches.

La date du jour est injectée (`aujourdhui`) pour des scénarios
déterministes, indépendants de la date réelle d'exécution des tests. On fixe
une référence au 15/06/2026 : mi-mois (il reste des jours avant la fin du
mois, condition de l'alerte) et toujours dans le passé par rapport à la vie
réelle du dépôt, pour que les transactions datées dans la fenêtre soient
acceptées par l'API.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.modules.analyse.service import (
    TYPE_NOTIF_ALERTE_SOLDE,
    notifier_ruptures_solde_proches,
    projeter_rupture_solde,
)
from app.modules.notifications.models import Notification
from tests.conftest import TestingSessionLocal, se_connecter

REF = date(2026, 6, 15)  # "aujourd'hui" fixe pour les tests


def _inscrire(client, email):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": "motdepasse123",
            "first_name": "Alerte",
            "last_name": "Solde",
            "phone": "+237600000000",
        },
    )
    token = se_connecter(client, email, "motdepasse123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    return headers, id_client


def _creer_compte(client, headers, solde_initial, nom="MoMo", type_="MOBILE_MONEY"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": type_, "solde_initial": solde_initial},
        headers=headers,
    ).json()


def _categorie(client, headers, nom="Alimentation"):
    categories = client.get("/api/v1/categories", headers=headers).json()
    return next(c for c in categories if c["nom"] == nom)


def _depense(client, headers, compte, categorie, montant, jour):
    return client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": montant,
            "type": "DEPENSE",
            "date": jour.isoformat(),
        },
        headers=headers,
    )


def test_projection_signale_un_compte_qui_part_a_zero_avant_la_fin_du_mois(client):
    headers, id_client = _inscrire(client, "alerte.rupture@example.com")
    # Solde de départ 100 000, puis 90 000 de dépenses dans la fenêtre des
    # 30 jours -> solde restant 10 000, rythme 3 000/jour -> ~3 jours de
    # réserve -> rupture le 18/06, avant la fin du mois (30/06).
    compte = _creer_compte(client, headers, solde_initial=100000)
    alimentation = _categorie(client, headers, "Alimentation")
    for jour, montant in ((5, 30000), (10, 30000), (14, 30000)):
        reponse = _depense(client, headers, compte, alimentation, montant, date(2026, 6, jour))
        assert reponse.status_code in (200, 201)

    session = TestingSessionLocal()
    try:
        projections = projeter_rupture_solde(session, id_client, aujourdhui=REF)
    finally:
        session.close()

    assert len(projections) == 1
    projection = projections[0]
    assert projection["id_compte"] == compte["id_compte"]
    assert Decimal(str(projection["solde"])) == Decimal("10000.00")
    assert projection["burn_quotidien"] == Decimal("3000")
    assert projection["date_rupture"] == date(2026, 6, 18)
    assert projection["categorie_principale"] == "Alimentation"
    assert projection["reduction_quotidienne"] > 0


def test_compte_qui_tient_jusqua_la_fin_du_mois_nest_pas_signale(client):
    headers, id_client = _inscrire(client, "alerte.ok@example.com")
    # Gros solde, dépenses minimes -> le compte tient très au-delà de la fin
    # du mois -> aucune alerte.
    compte = _creer_compte(client, headers, solde_initial=100000)
    alimentation = _categorie(client, headers, "Alimentation")
    assert _depense(client, headers, compte, alimentation, 300, date(2026, 6, 10)).status_code in (200, 201)

    session = TestingSessionLocal()
    try:
        projections = projeter_rupture_solde(session, id_client, aujourdhui=REF)
    finally:
        session.close()

    assert projections == []


def test_notification_creee_une_seule_fois_par_mois(client):
    headers, id_client = _inscrire(client, "alerte.notif@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    alimentation = _categorie(client, headers, "Alimentation")
    for jour, montant in ((5, 30000), (10, 30000), (14, 30000)):
        _depense(client, headers, compte, alimentation, montant, date(2026, 6, jour))

    session = TestingSessionLocal()
    try:
        nb_premier = notifier_ruptures_solde_proches(session, aujourdhui=REF)
        # Deuxième passage le même mois : l'anti-spam ne doit rien recréer.
        nb_deuxieme = notifier_ruptures_solde_proches(session, aujourdhui=REF)

        notifs = (
            session.query(Notification)
            .filter(
                Notification.id_utilisateur == id_client,
                Notification.type == TYPE_NOTIF_ALERTE_SOLDE,
            )
            .all()
        )
    finally:
        session.close()

    assert nb_premier == 1
    assert nb_deuxieme == 0
    assert len(notifs) == 1
    notif = notifs[0]
    assert notif.lien == f"/dashboard?compte={compte['id_compte']}"
    assert "Alimentation" in notif.message
    assert "18/06" in notif.message
