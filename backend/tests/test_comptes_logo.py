import os

from app.core.config import settings
from tests.conftest import se_connecter

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _connecte(client, email="logo.compte@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": "motdepasse123",
            "first_name": "Logo",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    token = se_connecter(client, email, "motdepasse123").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _creer(client, headers, **extra):
    corps = {"nom": "Ma banque", "type": "BANCAIRE", "solde_initial": 0, **extra}
    return client.post("/api/v1/comptes", json=corps, headers=headers)


def test_creer_compte_sans_logo_laisse_le_logo_vide(client):
    headers = _connecte(client, "logo.vide@example.com")
    reponse = _creer(client, headers)
    assert reponse.status_code == 201
    assert reponse.json()["logo"] is None


def test_creer_compte_avec_un_logo_predefini(client):
    headers = _connecte(client, "logo.predefini@example.com")
    reponse = _creer(client, headers, logo="/mobile-money/wave.jpg")
    assert reponse.status_code == 201
    assert reponse.json()["logo"] == "/mobile-money/wave.jpg"


def test_un_logo_externe_est_refuse(client):
    """Jamais d'URL arbitraire : un logo est affiché tel quel dans la page."""
    headers = _connecte(client, "logo.externe@example.com")
    for logo in ("https://exemple.com/pixel.png", "javascript:alert(1)", "/../secret.png", "/mobile-money/../x.png"):
        assert _creer(client, headers, logo=logo).status_code == 422


def test_modifier_le_logo_puis_le_retirer_avec_null(client):
    headers = _connecte(client, "logo.modifier@example.com")
    compte = _creer(client, headers).json()

    reponse = client.patch(f"/api/v1/comptes/{compte['id_compte']}", json={"logo": "/mobile-money/mtn.jpg"}, headers=headers)
    assert reponse.json()["logo"] == "/mobile-money/mtn.jpg"

    # Un PATCH qui ne parle pas du logo ne le touche pas.
    reponse = client.patch(f"/api/v1/comptes/{compte['id_compte']}", json={"nom": "Autre nom"}, headers=headers)
    assert reponse.json()["logo"] == "/mobile-money/mtn.jpg"

    reponse = client.patch(f"/api/v1/comptes/{compte['id_compte']}", json={"logo": None}, headers=headers)
    assert reponse.json()["logo"] is None


def test_importer_un_logo_l_heberge_et_l_associe_au_compte(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _connecte(client, "logo.import@example.com")
    compte = _creer(client, headers).json()

    reponse = client.post(
        f"/api/v1/comptes/{compte['id_compte']}/logo",
        headers=headers,
        files={"logo": ("logo.png", PNG_MAGIC + b"contenu-factice", "image/png")},
    )
    assert reponse.status_code == 200
    logo = reponse.json()["logo"]
    assert logo.startswith(f"{settings.BACKEND_URL}/avatars/compte_{compte['id_compte']}_")
    assert len(os.listdir(tmp_path)) == 1


def test_importer_un_second_logo_supprime_le_premier_fichier(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _connecte(client, "logo.remplace@example.com")
    compte = _creer(client, headers).json()
    url = f"/api/v1/comptes/{compte['id_compte']}/logo"
    fichier = {"logo": ("logo.png", PNG_MAGIC + b"x", "image/png")}

    client.post(url, headers=headers, files=fichier)
    client.post(url, headers=headers, files=fichier)

    assert len(os.listdir(tmp_path)) == 1


def test_choisir_un_logo_predefini_apres_un_import_supprime_le_fichier(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _connecte(client, "logo.bascule@example.com")
    compte = _creer(client, headers).json()
    client.post(
        f"/api/v1/comptes/{compte['id_compte']}/logo",
        headers=headers,
        files={"logo": ("logo.png", PNG_MAGIC + b"x", "image/png")},
    )
    assert len(os.listdir(tmp_path)) == 1

    reponse = client.patch(f"/api/v1/comptes/{compte['id_compte']}", json={"logo": "/cash.jpg"}, headers=headers)
    assert reponse.json()["logo"] == "/cash.jpg"
    assert os.listdir(tmp_path) == []


def test_retirer_le_logo_supprime_le_fichier(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _connecte(client, "logo.retirer@example.com")
    compte = _creer(client, headers).json()
    client.post(
        f"/api/v1/comptes/{compte['id_compte']}/logo",
        headers=headers,
        files={"logo": ("logo.png", PNG_MAGIC + b"x", "image/png")},
    )

    reponse = client.delete(f"/api/v1/comptes/{compte['id_compte']}/logo", headers=headers)
    assert reponse.status_code == 200
    assert reponse.json()["logo"] is None
    assert os.listdir(tmp_path) == []


def test_importer_rejette_un_format_non_supporte(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _connecte(client, "logo.gif@example.com")
    compte = _creer(client, headers).json()

    reponse = client.post(
        f"/api/v1/comptes/{compte['id_compte']}/logo",
        headers=headers,
        files={"logo": ("logo.svg", b"<svg onload=alert(1)></svg>", "image/svg+xml")},
    )
    assert reponse.status_code == 400
    assert os.listdir(tmp_path) == []


def test_importer_rejette_un_contenu_qui_ne_correspond_pas_au_type_declare(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers = _connecte(client, "logo.faux@example.com")
    compte = _creer(client, headers).json()

    reponse = client.post(
        f"/api/v1/comptes/{compte['id_compte']}/logo",
        headers=headers,
        files={"logo": ("logo.png", b"<script>alert(1)</script>", "image/png")},
    )
    assert reponse.status_code == 400
    assert os.listdir(tmp_path) == []


def test_importer_rejette_un_logo_trop_volumineux(client, tmp_path, monkeypatch):
    from app.modules.comptes import router as comptes_router

    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    monkeypatch.setattr(comptes_router, "TAILLE_MAX_LOGO", 10)
    headers = _connecte(client, "logo.gros@example.com")
    compte = _creer(client, headers).json()

    reponse = client.post(
        f"/api/v1/comptes/{compte['id_compte']}/logo",
        headers=headers,
        files={"logo": ("logo.png", PNG_MAGIC + b"x" * 50, "image/png")},
    )
    assert reponse.status_code == 400
    assert os.listdir(tmp_path) == []


def test_le_logo_d_un_autre_client_est_inaccessible(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AVATARS_DOSSIER", str(tmp_path))
    headers_a = _connecte(client, "logo.a@example.com")
    headers_b = _connecte(client, "logo.b@example.com")
    compte_a = _creer(client, headers_a).json()

    envoi = client.post(
        f"/api/v1/comptes/{compte_a['id_compte']}/logo",
        headers=headers_b,
        files={"logo": ("logo.png", PNG_MAGIC + b"x", "image/png")},
    )
    suppression = client.delete(f"/api/v1/comptes/{compte_a['id_compte']}/logo", headers=headers_b)

    assert envoi.status_code == 404
    assert suppression.status_code == 404
    assert os.listdir(tmp_path) == []
