from app.core.security import create_access_token, get_password_hash
from app.modules.auth.models import Administrateur
from app.modules.plans import service as plans_service
from tests.conftest import se_connecter


def _register_and_login(client, email="notif.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Notif",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _create_admin(db_session, username="notifadmin", email="notifadmin@mynkap.cm", password="adminpassword123"):
    admin = Administrateur(
        username=username,
        email=email,
        mot_de_passe=get_password_hash(password),
        niveau_acces=1,
        est_actif=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    token = create_access_token(subject=admin.id_administrateur)
    return admin, {"Authorization": f"Bearer {token}"}


def _creer_compte(client, headers, solde_initial=100000, nom="Compte principal"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


# --- Inscription : bienvenue côté client + signalement côté admin ---

def test_inscription_cree_une_notification_bienvenue_et_signale_les_admins(client, db_session):
    admin, admin_headers = _create_admin(db_session)
    # _register_and_login effectue aussi le login complet (OTP), qui crée sa
    # propre notification CONNEXION_REUSSIE — voir test_auth.py — d'où les
    # deux notifications (BIENVENUE + CONNEXION_REUSSIE) ci-dessous.
    headers = _register_and_login(client, "notif.inscription@example.com")

    mes_notifs = client.get("/api/v1/notifications", headers=headers).json()
    assert len(mes_notifs) == 2
    assert any(n["type"] == "BIENVENUE" and not n["est_lue"] for n in mes_notifs)

    notifs_admin = client.get("/api/v1/admin/notifications", headers=admin_headers).json()
    assert any(n["type"] == "NOUVEAU_CLIENT" for n in notifs_admin)


# --- Isolation entre clients + cycle lire/marquer lues ---

def test_client_ne_voit_que_ses_propres_notifications(client):
    headers_a = _register_and_login(client, "notif.clienta@example.com")
    headers_b = _register_and_login(client, "notif.clientb@example.com")

    notifs_a = client.get("/api/v1/notifications", headers=headers_a).json()
    notifs_b = client.get("/api/v1/notifications", headers=headers_b).json()
    assert len(notifs_a) == 2
    assert len(notifs_b) == 2

    id_notif_b = notifs_b[0]["id_notification"]
    # Un client ne peut pas marquer comme lue la notification d'un autre client.
    reponse = client.post(f"/api/v1/notifications/{id_notif_b}/lire", headers=headers_a)
    assert reponse.status_code == 404


def test_marquer_lue_et_compteur_non_lues(client):
    headers = _register_and_login(client, "notif.marquerlue@example.com")

    # BIENVENUE (inscription) + CONNEXION_REUSSIE (login complet effectué
    # par _register_and_login).
    compte = client.get("/api/v1/notifications/non-lues-count", headers=headers).json()
    assert compte["non_lues"] == 2

    id_notif = client.get("/api/v1/notifications", headers=headers).json()[0]["id_notification"]
    marquee = client.post(f"/api/v1/notifications/{id_notif}/lire", headers=headers)
    assert marquee.status_code == 200
    assert marquee.json()["est_lue"] is True

    compte_apres = client.get("/api/v1/notifications/non-lues-count", headers=headers).json()
    assert compte_apres["non_lues"] == 1


def test_marquer_toutes_les_notifications_lues(client, db_session):
    headers = _register_and_login(client, "notif.tout@example.com")
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]

    from app.modules.notifications import service as notifications_service
    notifications_service.creer_notification_client(db_session, id_client, "AUTRE", "Titre", "Message")

    # BIENVENUE + CONNEXION_REUSSIE + la notification "AUTRE" créée ci-dessus.
    assert client.get("/api/v1/notifications/non-lues-count", headers=headers).json()["non_lues"] == 3

    reponse = client.post("/api/v1/notifications/lire-tout", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["nb_marquees"] == 3
    assert client.get("/api/v1/notifications/non-lues-count", headers=headers).json()["non_lues"] == 0


# --- Accès admin réservé aux administrateurs ---

def test_notifications_admin_refusees_a_un_client(client):
    headers = _register_and_login(client, "notif.pasadmin@example.com")
    assert client.get("/api/v1/admin/notifications", headers=headers).status_code == 403


# --- Suppression (client) ---

def test_supprimer_une_notification_client(client):
    headers = _register_and_login(client, "notif.supprimer@example.com")
    notifs_avant = client.get("/api/v1/notifications", headers=headers).json()
    assert len(notifs_avant) == 2
    id_notif = notifs_avant[0]["id_notification"]

    reponse = client.delete(f"/api/v1/notifications/{id_notif}", headers=headers)
    assert reponse.status_code == 204

    notifs_apres = client.get("/api/v1/notifications", headers=headers).json()
    assert len(notifs_apres) == 1
    assert all(n["id_notification"] != id_notif for n in notifs_apres)


def test_supprimer_notification_dun_autre_client_renvoie_404(client):
    headers_a = _register_and_login(client, "notif.supprimer.a@example.com")
    headers_b = _register_and_login(client, "notif.supprimer.b@example.com")
    id_notif_b = client.get("/api/v1/notifications", headers=headers_b).json()[0]["id_notification"]

    reponse = client.delete(f"/api/v1/notifications/{id_notif_b}", headers=headers_a)
    assert reponse.status_code == 404
    # Toujours là côté B : la suppression tentée par A n'a rien touché.
    assert len(client.get("/api/v1/notifications", headers=headers_b).json()) == 2


def test_supprimer_toutes_les_notifications_client(client):
    headers = _register_and_login(client, "notif.supprimertout@example.com")
    assert len(client.get("/api/v1/notifications", headers=headers).json()) == 2

    reponse = client.delete("/api/v1/notifications", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["nb_marquees"] == 2
    assert client.get("/api/v1/notifications", headers=headers).json() == []


# --- Suppression (admin) ---

def test_supprimer_une_notification_admin(client, db_session):
    admin, admin_headers = _create_admin(db_session, email="notifadmin.suppr@mynkap.cm")
    _register_and_login(client, "notif.admin.suppr@example.com")  # génère NOUVEAU_CLIENT

    notifs_avant = client.get("/api/v1/admin/notifications", headers=admin_headers).json()
    assert len(notifs_avant) >= 1
    id_notif = notifs_avant[0]["id_notification"]

    reponse = client.delete(f"/api/v1/admin/notifications/{id_notif}", headers=admin_headers)
    assert reponse.status_code == 204
    assert all(n["id_notification"] != id_notif for n in client.get("/api/v1/admin/notifications", headers=admin_headers).json())


def test_supprimer_toutes_les_notifications_admin(client, db_session):
    admin, admin_headers = _create_admin(db_session, email="notifadmin.supprtout@mynkap.cm")
    _register_and_login(client, "notif.admin.supprtout@example.com")
    assert len(client.get("/api/v1/admin/notifications", headers=admin_headers).json()) >= 1

    reponse = client.delete("/api/v1/admin/notifications", headers=admin_headers)
    assert reponse.status_code == 200
    assert client.get("/api/v1/admin/notifications", headers=admin_headers).json() == []


def test_supprimer_notification_admin_refusee_a_un_client(client):
    headers = _register_and_login(client, "notif.admin.pasadmin@example.com")
    assert client.delete("/api/v1/admin/notifications/1", headers=headers).status_code == 403


# --- Alerte de budget (80%/100%) ---

def test_alerte_budget_100_cree_une_notification_client(client):
    headers = _register_and_login(client, "notif.budget@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    categorie = client.post(
        "/api/v1/categories", json={"nom": "Déplacements", "type": "DEPENSE"}, headers=headers
    ).json()
    client.post(
        "/api/v1/budgets",
        json={"id_categorie": categorie["id_categorie"], "montant_limite": 10000, "mois": 7, "annee": 2026},
        headers=headers,
    )

    client.post(
        "/api/v1/transactions",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 12000,
            "type": "DEPENSE",
            "date": "2026-07-24",
        },
        headers=headers,
    )

    # La lecture du budget calcule les valeurs et déclenche verifier_alertes().
    budgets = client.get("/api/v1/budgets", headers=headers).json()
    assert budgets[0]["alerte_100"] is True

    notifs = client.get("/api/v1/notifications", headers=headers).json()
    assert any(n["type"] == "BUDGET_100" for n in notifs)


# --- Paiement d'abonnement confirmé / échoué ---

def test_paiement_confirme_notifie_le_client_et_les_admins(client, db_session, monkeypatch):
    admin, admin_headers = _create_admin(db_session, email="notifadmin.paiement@mynkap.cm")
    headers = _register_and_login(client, "notif.paiementok@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_notif_success")

    client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_verifier_statut_hrpay", lambda reference: "SUCCESS")
    plans_service.verifier_paiements_en_attente(db_session)

    notifs = client.get("/api/v1/notifications", headers=headers).json()
    assert any(n["type"] == "PAIEMENT_CONFIRME" for n in notifs)

    notifs_admin = client.get("/api/v1/admin/notifications", headers=admin_headers).json()
    assert any(n["type"] == "PAIEMENT_RECU" for n in notifs_admin)


def test_paiement_echoue_notifie_le_client_uniquement(client, db_session, monkeypatch):
    admin, admin_headers = _create_admin(db_session, email="notifadmin.echec@mynkap.cm")
    headers = _register_and_login(client, "notif.paiementko@example.com")
    monkeypatch.setattr(plans_service, "_appeler_hrpay_cash_in", lambda *a, **k: "ref_notif_failed")

    client.post(
        "/api/v1/abonnement/paiements",
        json={
            "nom_plan": "ESSENTIEL",
            "cycle_facturation": "MENSUEL",
            "phone_number": "237655500393",
            "operator": "orange",
        },
        headers=headers,
    )

    monkeypatch.setattr(plans_service, "_verifier_statut_hrpay", lambda reference: "FAILED")
    plans_service.verifier_paiements_en_attente(db_session)

    notifs = client.get("/api/v1/notifications", headers=headers).json()
    assert any(n["type"] == "PAIEMENT_ECHEC" for n in notifs)

    # Pas de bruit côté admin pour un simple échec (évite le spam d'une
    # intégration HR-Skills Pay instable) — seul le succès est signalé.
    notifs_admin = client.get("/api/v1/admin/notifications", headers=admin_headers).json()
    assert not any(n["type"] == "PAIEMENT_RECU" for n in notifs_admin)
