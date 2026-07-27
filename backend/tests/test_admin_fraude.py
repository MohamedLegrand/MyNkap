import pytest
from datetime import date
from decimal import Decimal
from app.core.security import create_access_token, get_password_hash
from app.modules.audit.models import AuditLog
from app.modules.auth.models import Administrateur, Client
from app.modules.comptes.models import CompteFinancier, ComptePrincipal
from app.modules.transactions.models import Transaction

def _create_admin(db_session, username="fraudeadmin", email="fraudeadmin@mynkap.cm", password="adminpassword123", niveau_acces=3):
    admin = Administrateur(
        username=username,
        email=email,
        mot_de_passe=get_password_hash(password),
        niveau_acces=niveau_acces,
        est_actif=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    token = create_access_token(subject=admin.id_administrateur)
    return admin, {"Authorization": f"Bearer {token}"}

def _create_client_with_account(db_session, email="clientfraude@mynkap.cm", password="clientpassword123"):
    c = Client(
        email=email,
        first_name="Rigobert",
        last_name="Song",
        phone="+237699999998",
        mot_de_passe=get_password_hash(password),
        est_actif=True,
    )
    db_session.add(c)
    db_session.flush()

    cp = ComptePrincipal(id_client=c.id_client, solde_total=Decimal("500000.00"))
    db_session.add(cp)
    
    cf = CompteFinancier(
        id_client=c.id_client,
        nom="Compte Courant Test",
        type="COURANT",
        solde=Decimal("500000.00"),
        devise="XAF",
    )
    db_session.add(cf)
    db_session.commit()
    db_session.refresh(c)
    db_session.refresh(cf)

    token = create_access_token(subject=c.id_client)
    return c, cf, {"Authorization": f"Bearer {token}"}

def test_admin_fraude_overview_et_lister_transactions_suspectes(client, db_session):
    admin, admin_headers = _create_admin(db_session)
    user_c, compte, _ = _create_client_with_account(db_session, email="suspect1@mynkap.cm")

    # Transaction suspecte
    tx_suspecte = Transaction(
        id_client=user_c.id_client,
        id_compte=compte.id_compte,
        montant=Decimal("1500000.00"),
        type="DEPENSE",
        description="Achat volumineux inhabituel",
        date=date.today(),
        est_suspecte=True,
    )
    db_session.add(tx_suspecte)
    db_session.commit()

    # 1. Overview anti-fraude
    res_ov = client.get("/api/v1/admin/fraude/overview", headers=admin_headers)
    assert res_ov.status_code == 200
    data_ov = res_ov.json()
    assert data_ov["total_transactions_suspectes"] >= 1
    assert data_ov["nombre_clients_concernes"] >= 1
    assert Decimal(str(data_ov["montant_total_suspect"])) >= Decimal("1500000.00")

    # 2. Lister les transactions suspectes
    res_list = client.get("/api/v1/admin/fraude/transactions?est_suspecte=true", headers=admin_headers)
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["total"] >= 1
    assert any(item["id_transaction"] == tx_suspecte.id_transaction for item in data_list["items"])

def test_admin_fraude_detail_transaction_suspecte(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="detadmin", email="detadmin@mynkap.cm")
    user_c, compte, _ = _create_client_with_account(db_session, email="suspect2@mynkap.cm")

    tx = Transaction(
        id_client=user_c.id_client,
        id_compte=compte.id_compte,
        montant=Decimal("900000.00"),
        type="DEPENSE",
        description="Retrait d'urgence suspect",
        date=date.today(),
        est_suspecte=True,
    )
    db_session.add(tx)
    db_session.commit()

    res_det = client.get(f"/api/v1/admin/fraude/transactions/{tx.id_transaction}", headers=admin_headers)
    assert res_det.status_code == 200
    data = res_det.json()
    assert data["id_transaction"] == tx.id_transaction
    assert data["email_client"] == "suspect2@mynkap.cm"
    assert data["nombre_transactions_suspectes_client"] >= 1
    assert data["solde_compte_principal"] == "500000.00"

def test_admin_fraude_modifier_statut_suspicion(client, db_session):
    admin, admin_headers = _create_admin(db_session, username="modfraude", email="modfraude@mynkap.cm", niveau_acces=2)
    user_c, compte, _ = _create_client_with_account(db_session, email="suspect3@mynkap.cm")

    tx = Transaction(
        id_client=user_c.id_client,
        id_compte=compte.id_compte,
        montant=Decimal("750000.00"),
        type="DEPENSE",
        description="Achat suspect à vérifier",
        date=date.today(),
        est_suspecte=True,
    )
    db_session.add(tx)
    db_session.commit()

    # 1. Lever la suspicion
    res_lever = client.patch(
        f"/api/v1/admin/fraude/transactions/{tx.id_transaction}/statut",
        json={"est_suspecte": False, "raison": "Client a fourni son justificatif de dépense"},
        headers=admin_headers,
    )
    assert res_lever.status_code == 200
    assert res_lever.json()["est_suspecte"] is False

    # Vérification AuditLog
    log_lever = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_LEVER_SUSPICION",
        AuditLog.id_ressource == tx.id_transaction
    ).first()
    assert log_lever is not None

    # 2. Remarquer comme suspecte
    res_marquer = client.patch(
        f"/api/v1/admin/fraude/transactions/{tx.id_transaction}/statut",
        json={"est_suspecte": True, "raison": "Nouveau doute suite à un signalement bancaire"},
        headers=admin_headers,
    )
    assert res_marquer.status_code == 200
    assert res_marquer.json()["est_suspecte"] is True

    # AuditLog généré
    log_marquer = db_session.query(AuditLog).filter(
        AuditLog.action == "ADMIN_MARQUER_SUSPECTE",
        AuditLog.id_ressource == tx.id_transaction
    ).first()
    assert log_marquer is not None

def test_admin_fraude_restrictions_droits(client, db_session):
    # Admin niveau 1 (Support)
    _, l1_headers = _create_admin(db_session, username="fraudel1", email="fraudel1@mynkap.cm", niveau_acces=1)
    
    # Client normal
    user_c, compte, c_headers = _create_client_with_account(db_session, email="normalfraude@mynkap.cm")

    tx = Transaction(
        id_client=user_c.id_client,
        id_compte=compte.id_compte,
        montant=Decimal("400000.00"),
        type="DEPENSE",
        description="Transaction banale",
        date=date.today(),
        est_suspecte=False,
    )
    db_session.add(tx)
    db_session.commit()

    # 1. Admin Niveau 1 peut consulter l'overview -> 200 OK
    res_l1_ov = client.get("/api/v1/admin/fraude/overview", headers=l1_headers)
    assert res_l1_ov.status_code == 200

    # 2. Admin Niveau 1 NE PEUT PAS modifier la suspicion -> 403 Forbidden
    res_l1_mod = client.patch(
        f"/api/v1/admin/fraude/transactions/{tx.id_transaction}/statut",
        json={"est_suspecte": True},
        headers=l1_headers,
    )
    assert res_l1_mod.status_code == 403

    # 3. Client normal NE PEUT PAS consulter -> 403 Forbidden
    res_c_ov = client.get("/api/v1/admin/fraude/overview", headers=c_headers)
    assert res_c_ov.status_code == 403
