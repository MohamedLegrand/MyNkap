import pytest
from app.core.security import create_access_token, get_password_hash
from app.modules.auth.models import Administrateur, Client

def _create_admin(db_session, username="kpiadmin", email="kpiadmin@mynkap.cm", password="adminpassword123", niveau_acces=1):
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

def _create_client(db_session, email="kpiclient@mynkap.cm", password="clientpassword123"):
    c = Client(
        email=email,
        first_name="Patrick",
        last_name="Mboma",
        phone="+237699999997",
        mot_de_passe=get_password_hash(password),
        est_actif=True,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    token = create_access_token(subject=c.id_client)
    return c, {"Authorization": f"Bearer {token}"}

def test_admin_obtenir_kpis_globaux(client, db_session):
    admin, admin_headers = _create_admin(db_session)

    res = client.get("/api/v1/admin/kpis", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    # Vérification des blocs de KPIs
    assert "clients" in data
    assert "finances" in data
    assert "abonnements" in data
    assert "securite" in data

    # Vérification des champs clés
    assert "total_clients" in data["clients"]
    assert "clients_actifs" in data["clients"]
    assert "chiffre_affaires_abonnements" in data["finances"]
    assert "volume_total_transactions" in data["finances"]
    assert "taux_conversion_payant_pourcent" in data["abonnements"]
    assert "transactions_suspectes_count" in data["securite"]

def test_admin_kpis_restrictions_droits(client, db_session):
    user_c, c_headers = _create_client(db_session)

    # Un client normal ne peut pas accéder aux KPIs d'administration -> 403 Forbidden
    res = client.get("/api/v1/admin/kpis", headers=c_headers)
    assert res.status_code == 403
