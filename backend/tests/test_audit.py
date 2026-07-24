from app.modules.audit.models import AuditLog
from app.modules.audit.service import get_config, set_config


def _register_payload(**overrides):
    payload = {
        "email": "audit.test@example.com",
        "mot_de_passe": "motdepasse123",
        "first_name": "Audit",
        "last_name": "Test",
        "phone": "+237600000099",
    }
    payload.update(overrides)
    return payload


def test_register_and_login_are_audited(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    client.post(
        "/api/v1/auth/login",
        json={"email": "audit.test@example.com", "mot_de_passe": "motdepasse123"},
    )

    actions = [entry.action for entry in db_session.query(AuditLog).all()]
    assert "CREER" in actions
    assert "CONNEXION" in actions


def test_logout_is_audited(client, db_session):
    client.post("/api/v1/auth/register", json=_register_payload())
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "audit.test@example.com", "mot_de_passe": "motdepasse123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})

    actions = [entry.action for entry in db_session.query(AuditLog).all()]
    assert "DECONNEXION" in actions


def test_config_roundtrip_with_types(db_session):
    set_config(db_session, "plan.free.max_comptes", 3, type_="INT")
    set_config(db_session, "jarvis.actif", True, type_="BOOL")
    set_config(db_session, "plan.free.limites", {"transactions": 100}, type_="JSON")

    assert get_config(db_session, "plan.free.max_comptes") == 3
    assert get_config(db_session, "jarvis.actif") is True
    assert get_config(db_session, "plan.free.limites") == {"transactions": 100}
    assert get_config(db_session, "cle.inexistante", default="repli") == "repli"
