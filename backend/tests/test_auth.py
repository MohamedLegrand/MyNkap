def _register_payload(**overrides):
    payload = {
        "email": "jean.dupont@example.com",
        "mot_de_passe": "motdepasse123",
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+237600000000",
    }
    payload.update(overrides)
    return payload


def test_register_creates_client_with_default_profile(client):
    response = client.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jean.dupont@example.com"
    assert body["profile"]["devise"] == "XAF"
    assert body["profile"]["langue"] == "FR"


def test_register_rejects_duplicate_email(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    response = client.post("/api/v1/auth/register", json=_register_payload())

    assert response.status_code == 400


def test_login_with_correct_credentials_returns_tokens(client):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_is_rejected(client):
    client.post("/api/v1/auth/register", json=_register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "mauvais-mot-de-passe"},
    )

    assert response.status_code == 400


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_client_with_valid_token(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "jean.dupont@example.com"


def test_refresh_token_issues_new_access_token(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_logout_revokes_refresh_token(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "jean.dupont@example.com", "mot_de_passe": "motdepasse123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
