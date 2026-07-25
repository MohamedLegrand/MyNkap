from decimal import Decimal

import app.modules.jarvis.service as jarvis_service
from app.modules.plans import service as plans_service
from tests.conftest import TestingSessionLocal


def _upgrader_plan(id_client, nom_plan):
    """Passe directement par le service (jamais par HR-Skills Pay) — voir
    test_dettes.py pour le détail du partage de connexion StaticPool."""
    session = TestingSessionLocal()
    try:
        plans_service.changer_plan(session, id_client, nom_plan, "MENSUEL")
    finally:
        session.close()


def _register_and_login(client, email="jarvis.test@example.com", mot_de_passe="motdepasse123"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "mot_de_passe": mot_de_passe,
            "first_name": "Jarvis",
            "last_name": "Test",
            "phone": "+237600000000",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "mot_de_passe": mot_de_passe},
    )
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # JARVIS est réservé au palier PREMIUM (voir module Plans/Abonnement)
    # — un client GRATUIT/ESSENTIEL recevrait 403 partout ici.
    id_client = client.get("/api/v1/auth/me", headers=headers).json()["id_client"]
    _upgrader_plan(id_client, "PREMIUM")
    return headers


def _reponse_groq(**overrides):
    donnees = {
        "contenu": "Oui, vous pouvez vous permettre cette dépense.",
        "necessite_clarification": False,
        "options_suggerees": None,
        "peut_se_permettre": True,
        "montant_suggere": 5000,
        "conseil_supplementaire": "Pensez à garder une réserve.",
    }
    donnees.update(overrides)
    return donnees


def test_crud_conversation(client):
    headers = _register_and_login(client)

    creation = client.post("/api/v1/jarvis/conversations", json={"titre": "Question budget"}, headers=headers)
    assert creation.status_code == 201
    conversation = creation.json()
    assert conversation["titre"] == "Question budget"

    liste = client.get("/api/v1/jarvis/conversations", headers=headers).json()
    assert len(liste) == 1

    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["messages"] == []

    suppression = client.delete(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers)
    assert suppression.status_code == 204
    apres = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers)
    assert apres.status_code == 404


def test_conversation_dun_autre_client_renvoie_404(client):
    headers_a = _register_and_login(client, "jarvis.a@example.com")
    headers_b = _register_and_login(client, "jarvis.b@example.com")

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers_a).json()

    reponse = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers_b)
    assert reponse.status_code == 404


def test_poser_question_cree_question_et_reponse_avec_contexte_financier(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.question@example.com")
    client.post(
        "/api/v1/comptes", json={"nom": "Cash", "type": "ESPECES", "solde_initial": 100000}, headers=headers
    )

    contexte_capture = {}

    def fausse_reponse(system_prompt, historique, question):
        contexte_capture["system_prompt"] = system_prompt
        contexte_capture["historique"] = historique
        contexte_capture["question"] = question
        return _reponse_groq()

    monkeypatch.setattr(jarvis_service, "_appeler_groq", fausse_reponse)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "Puis-je me permettre 5000 XAF de dépense ?"},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["type"] == "REPONSE"
    assert body["peut_se_permettre"] is True
    assert Decimal(body["montant_suggere"]) == Decimal("5000")
    assert body["necessite_clarification"] is False

    # Le contexte financier réel a bien été injecté (pas juste un prompt générique)
    assert "100000" in contexte_capture["system_prompt"]
    assert contexte_capture["historique"] == []
    assert contexte_capture["question"] == "Puis-je me permettre 5000 XAF de dépense ?"

    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers).json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["type"] == "QUESTION"
    assert detail["messages"][1]["type"] == "REPONSE"
    # Titre auto-rempli à partir de la première question
    assert detail["titre"] == "Puis-je me permettre 5000 XAF de dépense ?"


def test_reponse_clarification_avec_options(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.clarification@example.com")

    def fausse_reponse(system_prompt, historique, question):
        return _reponse_groq(
            contenu="De quel type d'achat s'agit-il ?",
            necessite_clarification=True,
            options_suggerees=["Alimentation", "Loisirs", "Autre"],
            peut_se_permettre=None,
            montant_suggere=None,
            conseil_supplementaire=None,
        )

    monkeypatch.setattr(jarvis_service, "_appeler_groq", fausse_reponse)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "Je veux dépenser un peu d'argent"},
        headers=headers,
    )
    body = reponse.json()
    assert body["necessite_clarification"] is True
    assert body["options_suggerees"] == ["Alimentation", "Loisirs", "Autre"]
    assert body["peut_se_permettre"] is None
    assert body["montant_suggere"] is None


def test_service_ia_indisponible_conserve_la_question_et_renvoie_503(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.echec@example.com")

    def echec(system_prompt, historique, question):
        raise jarvis_service.ServiceIAIndisponibleError("timeout")

    monkeypatch.setattr(jarvis_service, "_appeler_groq", echec)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "Une question quelconque"},
        headers=headers,
    )
    assert reponse.status_code == 503

    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers).json()
    assert len(detail["messages"]) == 1
    assert detail["messages"][0]["type"] == "QUESTION"


def test_poser_question_sur_conversation_introuvable_renvoie_404(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.404@example.com")
    monkeypatch.setattr(jarvis_service, "_appeler_groq", lambda *a, **k: _reponse_groq())

    reponse = client.post(
        "/api/v1/jarvis/conversations/00000000-0000-0000-0000-000000000000/messages",
        json={"contenu": "Question"},
        headers=headers,
    )
    assert reponse.status_code == 404


# --- Chat vocal ---

def test_poser_question_vocale_transcrit_repond_et_synthetise(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.vocal@example.com")

    monkeypatch.setattr(jarvis_service, "_transcrire_audio", lambda *a, **k: "Puis-je me permettre 5000 XAF ?")
    monkeypatch.setattr(jarvis_service, "_appeler_groq", lambda *a, **k: _reponse_groq())
    monkeypatch.setattr(jarvis_service, "_synthetiser_voix", lambda texte: b"FAUX_AUDIO_WAV")

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages/vocal",
        files={"audio": ("question.wav", b"contenu audio factice", "audio/wav")},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["type"] == "REPONSE"
    assert body["canal"] == "VOCAL"
    assert body["audio_base64"] is not None

    import base64
    assert base64.b64decode(body["audio_base64"]) == b"FAUX_AUDIO_WAV"

    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers).json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["canal"] == "VOCAL"
    assert detail["messages"][0]["contenu"] == "Puis-je me permettre 5000 XAF ?"


def test_poser_question_vocale_echec_synthese_renvoie_texte_sans_audio(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.vocal.echecsynthese@example.com")

    monkeypatch.setattr(jarvis_service, "_transcrire_audio", lambda *a, **k: "Une question")
    monkeypatch.setattr(jarvis_service, "_appeler_groq", lambda *a, **k: _reponse_groq())

    def echec_synthese(texte):
        raise jarvis_service.ServiceIAIndisponibleError("panne TTS")

    monkeypatch.setattr(jarvis_service, "_synthetiser_voix", echec_synthese)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages/vocal",
        files={"audio": ("question.wav", b"contenu audio factice", "audio/wav")},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["audio_base64"] is None
    assert body["contenu"]  # la réponse texte reste bien présente


def test_poser_question_vocale_echec_transcription_renvoie_503(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.vocal.echectranscription@example.com")

    def echec_transcription(*a, **k):
        raise jarvis_service.ServiceIAIndisponibleError("audio incompréhensible")

    monkeypatch.setattr(jarvis_service, "_transcrire_audio", echec_transcription)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages/vocal",
        files={"audio": ("question.wav", b"contenu audio factice", "audio/wav")},
        headers=headers,
    )
    assert reponse.status_code == 503

    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers).json()
    assert len(detail["messages"]) == 0
