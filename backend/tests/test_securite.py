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
