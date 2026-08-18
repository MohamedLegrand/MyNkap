from datetime import date, timedelta
from decimal import Decimal

from app.modules.audit.models import AuditLog
from app.modules.plans import service as plans_service
from app.modules.transactions.models import Transaction, TransactionRecurrente
from app.modules.transactions.service import _avancer_date, verifier_et_executer_recurrences
from tests.conftest import TestingSessionLocal
from tests.conftest import se_connecter


def _upgrader_plan(id_client, nom_plan):
    """Passe directement par le service (jamais par HR-Skills Pay) — voir
    test_dettes.py pour le détail du partage de connexion StaticPool."""
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email="recurrentes.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Recurrente",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Récurrentes/Templates sont réservés au palier ESSENTIEL et plus (voir
    # module Plans/Abonnement) — un client GRATUIT recevrait 403 partout ici.
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "ESSENTIEL")
    return headers


def _creer_compte(client, headers, solde_initial=100000, nom="Compte principal"):
    return client.post(
        "/api/v1/comptes",
        json={"nom": nom, "type": "ESPECES", "solde_initial": solde_initial},
        headers=headers,
    ).json()


def _categorie(client, headers, nom="Logement"):
    categories = client.get("/api/v1/categories", headers=headers).json()
    return next(c for c in categories if c["nom"] == nom)


# --- _avancer_date : jour du mois qui n'existe pas partout ---

def test_avancer_date_cale_sur_le_dernier_jour_du_mois():
    assert _avancer_date(date(2026, 1, 31), "MENSUELLE") == date(2026, 2, 28)
    assert _avancer_date(date(2026, 1, 31), "TRIMESTRIELLE") == date(2026, 4, 30)
    assert _avancer_date(date(2026, 1, 31), "ANNUELLE") == date(2027, 1, 31)
    assert _avancer_date(date(2026, 1, 15), "HEBDOMADAIRE") == date(2026, 1, 22)


# --- CRUD ---

def test_crud_transaction_recurrente(client):
    headers = _register_and_login(client, "crud.recurrente@example.com")
    compte = _creer_compte(client, headers)
    categorie = _categorie(client, headers)

    creation = client.post(
        "/api/v1/transactions-recurrentes",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 25000,
            "type": "DEPENSE",
            "frequence": "MENSUELLE",
            "prochaine_execution": "2026-08-05",
        },
        headers=headers,
    )
    assert creation.status_code == 201
    recurrence = creation.json()
    assert recurrence["est_active"] is True
    assert recurrence["date_fin"] is None

    liste = client.get("/api/v1/transactions-recurrentes", headers=headers).json()
    assert len(liste) == 1

    modification = client.put(
        f"/api/v1/transactions-recurrentes/{recurrence['id_transaction_recurrente']}",
        json={"montant": 30000},
        headers=headers,
    )
    assert modification.status_code == 200
    assert modification.json()["montant"] == "30000.00"

    desactivation = client.delete(
        f"/api/v1/transactions-recurrentes/{recurrence['id_transaction_recurrente']}", headers=headers
    )
    assert desactivation.status_code == 204
    liste_apres = client.get("/api/v1/transactions-recurrentes", headers=headers).json()
    assert len(liste_apres) == 0

    reactivation = client.post(
        f"/api/v1/transactions-recurrentes/{recurrence['id_transaction_recurrente']}/reactiver", headers=headers
    )
    assert reactivation.status_code == 200
    assert reactivation.json()["est_active"] is True


# --- Le batch ---

def test_batch_execute_une_recurrence_due_et_avance_la_date(client, db_session):
    headers = _register_and_login(client, "batch.due@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    categorie = _categorie(client, headers)

    hier = date.today() - timedelta(days=1)
    recurrence = client.post(
        "/api/v1/transactions-recurrentes",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 25000,
            "type": "DEPENSE",
            "frequence": "MENSUELLE",
            "prochaine_execution": hier.isoformat(),
        },
        headers=headers,
    ).json()

    verifier_et_executer_recurrences(db_session)

    solde = Decimal(client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"])
    assert solde == Decimal("75000.00")

    recurrence_apres = client.get(
        f"/api/v1/transactions-recurrentes/{recurrence['id_transaction_recurrente']}", headers=headers
    ).json()
    assert recurrence_apres["prochaine_execution"] == _avancer_date(hier, "MENSUELLE").isoformat()

    # La transaction créée automatiquement est bien tracée
    transaction = (
        db_session.query(Transaction)
        .filter(Transaction.id_transaction_recurrente == recurrence["id_transaction_recurrente"])
        .one()
    )
    assert transaction.est_recurrente is True
    assert transaction.montant == Decimal("25000.00")


def test_batch_ignore_une_recurrence_pas_encore_due(client, db_session):
    headers = _register_and_login(client, "batch.pasdue@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    categorie = _categorie(client, headers)

    dans_5_jours = date.today() + timedelta(days=5)
    client.post(
        "/api/v1/transactions-recurrentes",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 25000,
            "type": "DEPENSE",
            "frequence": "MENSUELLE",
            "prochaine_execution": dans_5_jours.isoformat(),
        },
        headers=headers,
    )

    verifier_et_executer_recurrences(db_session)

    solde = Decimal(client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"])
    assert solde == Decimal("100000.00")


def test_batch_echec_solde_insuffisant_ne_fait_pas_avancer_la_date_et_retentera_demain(client, db_session):
    headers = _register_and_login(client, "batch.echec@example.com")
    compte = _creer_compte(client, headers, solde_initial=1000)
    categorie = _categorie(client, headers)

    hier = date.today() - timedelta(days=1)
    recurrence = client.post(
        "/api/v1/transactions-recurrentes",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 25000,
            "type": "DEPENSE",
            "frequence": "MENSUELLE",
            "prochaine_execution": hier.isoformat(),
        },
        headers=headers,
    ).json()

    verifier_et_executer_recurrences(db_session)

    # Rien débité, la récurrence reste due (elle retentera au prochain passage)
    solde = Decimal(client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"])
    assert solde == Decimal("1000.00")

    recurrence_apres = client.get(
        f"/api/v1/transactions-recurrentes/{recurrence['id_transaction_recurrente']}", headers=headers
    ).json()
    assert recurrence_apres["prochaine_execution"] == hier.isoformat()
    assert recurrence_apres["est_active"] is True

    logs = db_session.query(AuditLog).filter(AuditLog.action == "ECHEC_TRANSACTION_RECURRENTE").all()
    assert len(logs) == 1


def test_batch_desactive_automatiquement_apres_date_fin(client, db_session):
    headers = _register_and_login(client, "batch.datefin@example.com")
    compte = _creer_compte(client, headers, solde_initial=100000)
    categorie = _categorie(client, headers)

    hier = date.today() - timedelta(days=1)
    recurrence = client.post(
        "/api/v1/transactions-recurrentes",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "montant": 5000,
            "type": "DEPENSE",
            "frequence": "MENSUELLE",
            "prochaine_execution": hier.isoformat(),
            "date_fin": date.today().isoformat(),
        },
        headers=headers,
    ).json()

    verifier_et_executer_recurrences(db_session)

    recurrence_apres = client.get(
        f"/api/v1/transactions-recurrentes/{recurrence['id_transaction_recurrente']}", headers=headers
    ).json()
    # prochaine_execution (hier + 1 mois) dépasse date_fin (aujourd'hui)
    assert recurrence_apres["est_active"] is False


# --- Templates ---

def test_crud_template_et_rejouer(client):
    headers = _register_and_login(client, "template.test@example.com")
    compte = _creer_compte(client, headers, solde_initial=50000)
    categorie = _categorie(client, headers, nom="Autres dépenses")

    creation = client.post(
        "/api/v1/templates",
        json={
            "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"],
            "nom": "Crédit téléphone",
            "montant": 1000,
            "type": "DEPENSE",
        },
        headers=headers,
    )
    assert creation.status_code == 201
    template = creation.json()
    assert template["nombre_utilisations"] == 0

    rejoue_1 = client.post(f"/api/v1/templates/{template['id_template']}/rejouer", headers=headers)
    assert rejoue_1.status_code == 201
    assert rejoue_1.json()["montant"] == "1000.00"

    rejoue_2 = client.post(f"/api/v1/templates/{template['id_template']}/rejouer", headers=headers)
    assert rejoue_2.status_code == 201

    solde = Decimal(client.get(f"/api/v1/comptes/{compte['id_compte']}", headers=headers).json()["solde"])
    assert solde == Decimal("48000.00")

    template_apres = client.get(f"/api/v1/templates/{template['id_template']}", headers=headers).json()
    assert template_apres["nombre_utilisations"] == 2

    # Désactivation : rejouer devient impossible
    client.delete(f"/api/v1/templates/{template['id_template']}", headers=headers)
    rejoue_bloque = client.post(f"/api/v1/templates/{template['id_template']}/rejouer", headers=headers)
    assert rejoue_bloque.status_code == 404

    reactivation = client.post(f"/api/v1/templates/{template['id_template']}/reactiver", headers=headers)
    assert reactivation.status_code == 200

    rejoue_apres_reactivation = client.post(f"/api/v1/templates/{template['id_template']}/rejouer", headers=headers)
    assert rejoue_apres_reactivation.status_code == 201


def test_liste_templates_triee_par_nombre_utilisations(client):
    headers = _register_and_login(client, "template.tri@example.com")
    compte = _creer_compte(client, headers, solde_initial=50000)
    categorie = _categorie(client, headers, nom="Autres dépenses")

    peu_utilise = client.post(
        "/api/v1/templates",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie["id_categorie"], "nom": "Peu utilisé", "montant": 500, "type": "DEPENSE"},
        headers=headers,
    ).json()
    tres_utilise = client.post(
        "/api/v1/templates",
        json={"id_compte": compte["id_compte"], "id_categorie": categorie["id_categorie"], "nom": "Très utilisé", "montant": 500, "type": "DEPENSE"},
        headers=headers,
    ).json()

    client.post(f"/api/v1/templates/{tres_utilise['id_template']}/rejouer", headers=headers)
    client.post(f"/api/v1/templates/{tres_utilise['id_template']}/rejouer", headers=headers)
    client.post(f"/api/v1/templates/{peu_utilise['id_template']}/rejouer", headers=headers)

    liste = client.get("/api/v1/templates", headers=headers).json()
    assert liste[0]["nom"] == "Très utilisé"
    assert liste[1]["nom"] == "Peu utilisé"
