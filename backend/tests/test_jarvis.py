from decimal import Decimal

import app.modules.jarvis.service as jarvis_service
from app.modules.plans import service as plans_service
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
    access_token = se_connecter(client, email, mot_de_passe).json()["access_token"]
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
        "actions": [],
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


# --- Actions proposées par JARVIS (créer transaction / créer compte) ---

def test_jarvis_propose_une_transaction_en_attente_de_confirmation(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.action.tx@example.com")
    compte = client.post(
        "/api/v1/comptes", json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": 50000}, headers=headers
    ).json()
    categorie = next(
        c for c in client.get("/api/v1/categories", headers=headers).json() if c["type"] == "DEPENSE"
    )

    def fausse_reponse(system_prompt, historique, question):
        # Le catalogue de comptes/catégories réels doit être injecté dans le prompt.
        assert str(compte["id_compte"]) in system_prompt
        assert str(categorie["id_categorie"]) in system_prompt
        return _reponse_groq(
            contenu="Je vais enregistrer votre dépense de 2000 XAF.",
            actions=[{
                "type": "CREER_TRANSACTION", "id_compte": compte["id_compte"],
                "id_categorie": categorie["id_categorie"], "montant": 2000,
                "type_transaction": "DEPENSE", "description": "Courses au marché",
            }],
        )

    monkeypatch.setattr(jarvis_service, "_appeler_groq", fausse_reponse)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "J'ai dépensé 2000 pour manger"},
        headers=headers,
    )
    body = reponse.json()
    assert len(body["actions"]) == 1
    action = body["actions"][0]
    assert action["type_action"] == "CREER_TRANSACTION"
    assert action["statut"] == "EN_ATTENTE"
    assert "2000" in action["resume"]

    # Seul le DEPOT_INITIAL du compte existe pour l'instant — la dépense
    # proposée par JARVIS n'est pas encore confirmée.
    avant = client.get("/api/v1/transactions", headers=headers).json()
    assert len(avant) == 1
    assert avant[0]["type"] == "DEPOT_INITIAL"

    confirmation = client.post(f"/api/v1/jarvis/actions/{action['id_action']}/confirmer", headers=headers)
    assert confirmation.status_code == 200
    assert confirmation.json()["statut"] == "EXECUTE"

    transactions = client.get("/api/v1/transactions", headers=headers).json()
    assert len(transactions) == 2
    depense = next(t for t in transactions if t["type"] == "DEPENSE")
    assert Decimal(depense["montant"]) == Decimal("2000")

    # Une action déjà exécutée ne peut plus être reconfirmée.
    reconfirmation = client.post(f"/api/v1/jarvis/actions/{action['id_action']}/confirmer", headers=headers)
    assert reconfirmation.status_code == 404


def test_jarvis_propose_plusieurs_actions_dans_un_seul_message(client, monkeypatch):
    """
    "Aujourd'hui j'ai fait plusieurs achats" décrit plusieurs transactions
    en une seule phrase — chacune doit ressortir comme une action distincte,
    confirmable indépendamment des autres.
    """
    headers = _register_and_login(client, "jarvis.action.multiple@example.com")
    compte = client.post(
        "/api/v1/comptes", json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": 50000}, headers=headers
    ).json()
    categorie = next(
        c for c in client.get("/api/v1/categories", headers=headers).json() if c["type"] == "DEPENSE"
    )

    monkeypatch.setattr(
        jarvis_service, "_appeler_groq",
        lambda *a, **k: _reponse_groq(actions=[
            {
                "type": "CREER_TRANSACTION", "id_compte": compte["id_compte"],
                "id_categorie": categorie["id_categorie"], "montant": 2000,
                "type_transaction": "DEPENSE", "description": "Marché",
            },
            {
                "type": "CREER_TRANSACTION", "id_compte": compte["id_compte"],
                "id_categorie": categorie["id_categorie"], "montant": 500,
                "type_transaction": "DEPENSE", "description": "Taxi",
            },
        ]),
    )

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "Aujourd'hui j'ai dépensé 2000 au marché et 500 en taxi"},
        headers=headers,
    )
    actions = reponse.json()["actions"]
    assert len(actions) == 2
    assert {a["statut"] for a in actions} == {"EN_ATTENTE"}

    # Confirmer la première n'affecte pas la seconde.
    client.post(f"/api/v1/jarvis/actions/{actions[0]['id_action']}/confirmer", headers=headers)
    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers).json()
    actions_apres = detail["messages"][1]["actions"]
    statuts_par_id = {a["id_action"]: a["statut"] for a in actions_apres}
    assert statuts_par_id[actions[0]["id_action"]] == "EXECUTE"
    assert statuts_par_id[actions[1]["id_action"]] == "EN_ATTENTE"

    transactions = client.get("/api/v1/transactions", headers=headers).json()
    depenses = [t for t in transactions if t["type"] == "DEPENSE"]
    assert len(depenses) == 1
    assert Decimal(depenses[0]["montant"]) == Decimal("2000")


def test_jarvis_ignore_une_action_avec_id_compte_hallucine(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.action.hallucination@example.com")

    def fausse_reponse(system_prompt, historique, question):
        return _reponse_groq(actions=[{
            "type": "CREER_TRANSACTION", "id_compte": 999999, "id_categorie": 999999,
            "montant": 2000, "type_transaction": "DEPENSE",
        }])

    monkeypatch.setattr(jarvis_service, "_appeler_groq", fausse_reponse)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "J'ai dépensé 2000 pour manger"},
        headers=headers,
    )
    # Aucune action n'est proposée : l'id_compte n'appartient pas au client.
    assert reponse.json()["actions"] == []


def test_jarvis_propose_creer_un_compte(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.action.compte@example.com")

    def fausse_reponse(system_prompt, historique, question):
        return _reponse_groq(actions=[{
            "type": "CREER_COMPTE", "nom": "Épargne vacances", "type_compte": "EPARGNE",
            "devise": "XAF", "solde_initial": 20000,
        }])

    monkeypatch.setattr(jarvis_service, "_appeler_groq", fausse_reponse)

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "Crée-moi un compte épargne vacances avec 20000"},
        headers=headers,
    )
    action = reponse.json()["actions"][0]
    assert action["type_action"] == "CREER_COMPTE"

    confirmation = client.post(f"/api/v1/jarvis/actions/{action['id_action']}/confirmer", headers=headers)
    assert confirmation.status_code == 200

    comptes = client.get("/api/v1/comptes", headers=headers).json()
    assert any(c["nom"] == "Épargne vacances" for c in comptes)


def test_jarvis_propose_une_action_via_le_canal_vocal(client, monkeypatch):
    """
    Le vocal transcrit puis appelle le même poser_question() que le texte
    (voir poser_question_vocale) — les actions proposées doivent donc
    apparaître à l'identique dans la réponse vocale, et rester exécutables
    via /jarvis/actions/{id}/confirmer comme n'importe quelle action issue
    du chat écrit.
    """
    headers = _register_and_login(client, "jarvis.action.vocal@example.com")
    compte = client.post(
        "/api/v1/comptes", json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": 50000}, headers=headers
    ).json()
    categorie = next(
        c for c in client.get("/api/v1/categories", headers=headers).json() if c["type"] == "DEPENSE"
    )

    monkeypatch.setattr(jarvis_service, "_transcrire_audio", lambda *a, **k: "J'ai dépensé 2000 pour manger")
    monkeypatch.setattr(
        jarvis_service, "_appeler_groq",
        lambda *a, **k: _reponse_groq(actions=[{
            "type": "CREER_TRANSACTION", "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"], "montant": 2000, "type_transaction": "DEPENSE",
        }]),
    )
    monkeypatch.setattr(jarvis_service, "_synthetiser_voix", lambda texte: b"FAUX_AUDIO_WAV")

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages/vocal",
        files={"audio": ("question.wav", b"contenu audio factice", "audio/wav")},
        headers=headers,
    )
    assert reponse.status_code == 201
    body = reponse.json()
    assert body["canal"] == "VOCAL"
    assert len(body["actions"]) == 1
    action = body["actions"][0]
    assert action["type_action"] == "CREER_TRANSACTION"
    assert action["statut"] == "EN_ATTENTE"

    # Rejouée via GET (comme le fait le frontend après un message vocal) :
    # l'action proposée doit toujours être là.
    detail = client.get(f"/api/v1/jarvis/conversations/{conversation['id_conversation']}", headers=headers).json()
    action_dans_historique = detail["messages"][1]["actions"][0]
    assert action_dans_historique["id_action"] == action["id_action"]

    confirmation = client.post(f"/api/v1/jarvis/actions/{action['id_action']}/confirmer", headers=headers)
    assert confirmation.status_code == 200
    assert confirmation.json()["statut"] == "EXECUTE"

    transactions = client.get("/api/v1/transactions", headers=headers).json()
    depense = next(t for t in transactions if t["type"] == "DEPENSE")
    assert Decimal(depense["montant"]) == Decimal("2000")


def test_jarvis_annuler_une_action_empeche_toute_execution(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.action.annuler@example.com")
    compte = client.post(
        "/api/v1/comptes", json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": 50000}, headers=headers
    ).json()
    categorie = next(
        c for c in client.get("/api/v1/categories", headers=headers).json() if c["type"] == "DEPENSE"
    )

    monkeypatch.setattr(
        jarvis_service, "_appeler_groq",
        lambda *a, **k: _reponse_groq(actions=[{
            "type": "CREER_TRANSACTION", "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"], "montant": 2000, "type_transaction": "DEPENSE",
        }]),
    )

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "J'ai dépensé 2000 pour manger"},
        headers=headers,
    )
    action = reponse.json()["actions"][0]

    annulation = client.post(f"/api/v1/jarvis/actions/{action['id_action']}/annuler", headers=headers)
    assert annulation.status_code == 200
    assert annulation.json()["statut"] == "ANNULE"

    # Seul le DEPOT_INITIAL du compte existe — la dépense annulée n'a jamais été créée.
    transactions = client.get("/api/v1/transactions", headers=headers).json()
    assert len(transactions) == 1
    assert transactions[0]["type"] == "DEPOT_INITIAL"

    confirmation_apres_annulation = client.post(
        f"/api/v1/jarvis/actions/{action['id_action']}/confirmer", headers=headers
    )
    assert confirmation_apres_annulation.status_code == 404


def test_jarvis_confirmer_une_action_expiree_la_marque_annulee(client, monkeypatch):
    headers = _register_and_login(client, "jarvis.action.expiree@example.com")
    compte = client.post(
        "/api/v1/comptes", json={"nom": "MOMO", "type": "MOBILE_MONEY", "solde_initial": 50000}, headers=headers
    ).json()
    categorie = next(
        c for c in client.get("/api/v1/categories", headers=headers).json() if c["type"] == "DEPENSE"
    )

    monkeypatch.setattr(
        jarvis_service, "_appeler_groq",
        lambda *a, **k: _reponse_groq(actions=[{
            "type": "CREER_TRANSACTION", "id_compte": compte["id_compte"],
            "id_categorie": categorie["id_categorie"], "montant": 2000, "type_transaction": "DEPENSE",
        }]),
    )

    conversation = client.post("/api/v1/jarvis/conversations", json={}, headers=headers).json()
    reponse = client.post(
        f"/api/v1/jarvis/conversations/{conversation['id_conversation']}/messages",
        json={"contenu": "J'ai dépensé 2000 pour manger"},
        headers=headers,
    )
    id_action = reponse.json()["actions"][0]["id_action"]

    import uuid
    from datetime import datetime, timedelta
    from app.modules.jarvis.models import ActionIA
    session = TestingSessionLocal()
    try:
        action_db = session.query(ActionIA).filter(ActionIA.id_action == uuid.UUID(id_action)).first()
        action_db.date_expiration = datetime.utcnow() - timedelta(minutes=1)
        session.commit()
    finally:
        session.close()

    confirmation = client.post(f"/api/v1/jarvis/actions/{id_action}/confirmer", headers=headers)
    assert confirmation.status_code == 400

    # Seul le DEPOT_INITIAL du compte existe — l'action expirée n'a jamais été exécutée.
    transactions = client.get("/api/v1/transactions", headers=headers).json()
    assert len(transactions) == 1
    assert transactions[0]["type"] == "DEPOT_INITIAL"


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
