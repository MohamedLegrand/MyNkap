def test_les_reponses_portent_les_entetes_de_securite_de_base(client):
    """
    Voir main.EntetesSecuriteMiddleware — durcissement absent par défaut
    chez FastAPI/Starlette (aucune route ne les pose individuellement).
    """
    reponse = client.get("/api/v1/plans")

    assert reponse.headers["X-Content-Type-Options"] == "nosniff"
    assert reponse.headers["X-Frame-Options"] == "DENY"
    assert reponse.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "microphone=()" in reponse.headers["Permissions-Policy"]
    assert "max-age" in reponse.headers["Strict-Transport-Security"]


def test_jeton_avec_sub_non_numerique_renvoie_401_pas_500(client):
    """
    Voir auth.dependencies.get_current_user : un jeton correctement signé
    mais avec un "sub" non numérique (jeton bricolé, ou bug côté émetteur)
    levait ValueError sur int(user_id), non intercepté par le seul `except
    JWTError` — remontait donc en 500 au lieu d'un simple 401.
    """
    from app.core.security import create_access_token

    jeton = create_access_token(subject="pas-un-entier")
    reponse = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {jeton}"})
    assert reponse.status_code == 401


def test_changer_mot_de_passe_est_limite_en_debit(client, db_session):
    """
    Voir auth.router.changer_mon_mot_de_passe : contrairement à /auth/login,
    un échec ici n'incrémente aucun compteur de verrouillage de compte
    (mot_de_passe_actuel n'est vérifié que face à un jeton déjà valide) —
    sans limite de débit dédiée, un jeton de session volé permettrait de
    tester le mot de passe actuel sans aucun frein.
    """
    from tests.conftest import se_connecter

    email = "ratelimit.changepwd@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email, "mot_de_passe": "motdepasse123",
            "first_name": "Rate", "last_name": "Limit", "phone": "+237600000001",
        },
    )
    headers = {"Authorization": f"Bearer {se_connecter(client, email, 'motdepasse123').json()['access_token']}"}

    corps = {"mot_de_passe_actuel": "mauvais_mdp", "nouveau_mot_de_passe": "nouveaumdp123"}
    codes = [client.put("/api/v1/auth/change-password", json=corps, headers=headers).status_code for _ in range(6)]
    assert 429 in codes
