import base64
import io
import json
import wave
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.budgets import service as budgets_service
from app.modules.comptes import service as comptes_service
from app.modules.dettes import service as dettes_service
from app.modules.epargne import service as epargne_service
from app.modules.jarvis.models import Conversation, Message

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# whisper-large-v3 (pas la variante "turbo") : la précision prime sur la
# latence ici — un montant mal transcrit ("15 000" entendu "50 000")
# fausserait tout le raisonnement financier en aval.
GROQ_WHISPER_MODEL = "whisper-large-v3"

GEMINI_TTS_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
GEMINI_TTS_VOICE = "Kore"
GEMINI_TTS_SAMPLE_RATE = 24000

# Nombre de messages précédents (question + réponse confondues) envoyés
# comme contexte à chaque nouvel appel — pas de résumé/compression, une
# limite simple suffit vu la taille du reste du projet.
NB_MESSAGES_CONTEXTE = 10

SYSTEM_PROMPT_TEMPLATE = """Tu es JARVIS, l'assistant financier de MyNkap, un expert en finance \
personnelle et en comptabilité pour le marché d'Afrique Centrale (XAF).

Ton comportement :
- Tu vouvoies toujours l'utilisateur, avec un ton professionnel, courtois et bienveillant.
- Tu ne devines jamais : si la question est ambiguë ou qu'il te manque une information pour \
répondre avec certitude, tu demandes une clarification au lieu de répondre à côté. Propose si \
possible 2 à 4 choix clairs (QCM) pour que l'utilisateur puisse sélectionner sa réponse plutôt \
que de la retaper.
- Tu bases tes réponses financières UNIQUEMENT sur les données réelles fournies ci-dessous. Tu \
n'inventes jamais de chiffres.
- Tu ne peux créer, modifier ou supprimer aucune donnée — tu conseilles seulement.

Situation financière actuelle du client :
{contexte_financier}

Tu dois TOUJOURS répondre en JSON valide, avec exactement cette forme, sans aucun texte en dehors :
{{
  "contenu": "ta réponse en français, claire et concise",
  "necessite_clarification": true ou false,
  "options_suggerees": ["option 1", "option 2"] ou null si necessite_clarification est false,
  "peut_se_permettre": true, false ou null si la question ne porte pas sur un achat,
  "montant_suggere": nombre ou null,
  "conseil_supplementaire": "un conseil court" ou null
}}
"""


class ConversationIntrouvableError(Exception):
    """La conversation n'existe pas ou n'appartient pas au client."""


class ServiceIAIndisponibleError(Exception):
    """L'appel au fournisseur IA a échoué (réseau, clé invalide, quota, réponse invalide...)."""


def creer_conversation(db: Session, id_client: int, titre: Optional[str] = None) -> Conversation:
    conversation = Conversation(id_client=id_client, titre=titre)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def lister_conversations(db: Session, id_client: int) -> List[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.id_client == id_client)
        .order_by(Conversation.date_dernier_message.desc())
        .all()
    )


def obtenir_conversation_du_client(db: Session, id_conversation: UUID, id_client: int) -> Optional[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.id_conversation == id_conversation, Conversation.id_client == id_client)
        .first()
    )


def supprimer_conversation(db: Session, id_conversation: UUID, id_client: int) -> None:
    """
    Suppression réelle (pas de soft-delete) : contrairement au reste du
    projet, une conversation n'est pas un enregistrement financier — rien
    dans le patrimoine/l'historique comptable n'en dépend.
    """
    conversation = obtenir_conversation_du_client(db, id_conversation, id_client)
    if conversation is None:
        raise ConversationIntrouvableError()
    db.delete(conversation)
    db.commit()


def _construire_contexte_financier(db: Session, id_client: int) -> str:
    """Vue lecture seule de la situation financière réelle du client,
    injectée dans le prompt pour que JARVIS ne réponde jamais en devinant
    des chiffres."""
    compte_principal = comptes_service.synchroniser_compte_principal(db, id_client)
    patrimoine_net = comptes_service.calculer_patrimoine_net(db, id_client)
    comptes = comptes_service.lister_comptes(db, id_client)

    lignes = [
        f"- Solde total (tous comptes) : {compte_principal.solde_total} XAF",
        f"- Patrimoine net (solde - dettes + créances) : {patrimoine_net} XAF",
    ]

    lignes.append("- Comptes :" if comptes else "- Comptes : aucun")
    for compte in comptes:
        lignes.append(f"  - {compte.nom} ({compte.type}) : {compte.solde} XAF")

    budgets = budgets_service.lister_budgets(db, id_client)
    if budgets:
        lignes.append("- Budgets du mois en cours :")
        for budget, valeurs in budgets:
            lignes.append(
                f"  - {budget.categorie.nom} : {valeurs['montant_depense']}/{budget.montant_limite} XAF "
                f"dépensés ({valeurs['pourcentage_utilise']:.0f}%)"
            )

    dettes_actives = [d for d in dettes_service.lister_dettes(db, id_client, "DETTE") if d.statut != "SOLDE"]
    if dettes_actives:
        lignes.append("- Dettes en cours :")
        for dette in dettes_actives:
            lignes.append(f"  - {dette.nom} : {dette.get_montant_restant()} XAF restants")

    creances_actives = [
        c for c in dettes_service.lister_dettes(db, id_client, "CREANCE") if c.statut not in ("SOLDE", "PERTE")
    ]
    if creances_actives:
        lignes.append("- Créances en cours :")
        for creance in creances_actives:
            lignes.append(f"  - {creance.nom} : {creance.get_montant_restant()} XAF à recevoir")

    objectifs = epargne_service.lister_objectifs(db, id_client)
    if objectifs:
        lignes.append("- Objectifs d'épargne :")
        for objectif in objectifs:
            valeurs = epargne_service.calculer_valeurs_objectif(objectif)
            lignes.append(
                f"  - {objectif.nom} : {valeurs['montant_actuel']}/{objectif.montant_cible} XAF ({objectif.statut})"
            )

    return "\n".join(lignes)


def _construire_historique(conversation: Conversation) -> List[dict]:
    """Historique avant l'ajout de la nouvelle question (celle-ci est
    envoyée séparément par poser_question, jamais dupliquée ici)."""
    role_par_type = {"QUESTION": "user", "REPONSE": "assistant"}
    messages_precedents = conversation.messages[-NB_MESSAGES_CONTEXTE:]
    return [{"role": role_par_type[m.type], "content": m.contenu} for m in messages_precedents]


def _appeler_groq(system_prompt: str, historique: List[dict], question: str) -> dict:
    """
    Appel structuré (JSON mode) à l'API Groq, compatible OpenAI — pas de
    SDK dédié nécessaire, un simple appel HTTP suffit. Gemini reste
    configuré (settings.GEMINI_API_KEY) mais n'est pas utilisé ici, réservé
    à un usage futur (OCR, vocal...).
    """
    messages = [{"role": "system", "content": system_prompt}, *historique, {"role": "user", "content": question}]

    try:
        reponse = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=20.0,
        )
        reponse.raise_for_status()
        contenu_brut = reponse.json()["choices"][0]["message"]["content"]
        return json.loads(contenu_brut)
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as erreur:
        raise ServiceIAIndisponibleError(str(erreur))


def poser_question(db: Session, id_client: int, id_conversation: UUID, contenu: str, canal: str = "TEXTE") -> Message:
    conversation = obtenir_conversation_du_client(db, id_conversation, id_client)
    if conversation is None:
        raise ConversationIntrouvableError()

    historique = _construire_historique(conversation)

    question = Message(id_conversation=conversation.id_conversation, contenu=contenu, type="QUESTION", canal=canal)
    db.add(question)

    contexte_financier = _construire_contexte_financier(db, id_client)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(contexte_financier=contexte_financier)

    try:
        donnees = _appeler_groq(system_prompt, historique, contenu)
    except ServiceIAIndisponibleError:
        # La question reste enregistrée même si JARVIS n'a pas pu répondre
        # — rien n'est perdu, le client peut réessayer.
        db.commit()
        raise

    montant_brut = donnees.get("montant_suggere")

    reponse = Message(
        id_conversation=conversation.id_conversation,
        contenu=donnees.get("contenu") or "",
        type="REPONSE",
        canal=canal,
        necessite_clarification=bool(donnees.get("necessite_clarification", False)),
        options_suggerees=donnees.get("options_suggerees"),
        peut_se_permettre=donnees.get("peut_se_permettre"),
        montant_suggere=Decimal(str(montant_brut)) if montant_brut is not None else None,
        conseil_supplementaire=donnees.get("conseil_supplementaire"),
    )
    db.add(reponse)

    conversation.date_dernier_message = datetime.utcnow()
    if conversation.titre is None:
        conversation.titre = contenu[:100]

    db.commit()
    db.refresh(reponse)
    return reponse


def _pcm_vers_wav(pcm: bytes, sample_rate: int = GEMINI_TTS_SAMPLE_RATE) -> bytes:
    """Gemini renvoie du PCM brut (mono, 16 bits) sans en-tête — on
    l'enveloppe dans un conteneur WAV standard pour qu'il soit lisible par
    n'importe quel lecteur audio côté client."""
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as fichier_wav:
        fichier_wav.setnchannels(1)
        fichier_wav.setsampwidth(2)
        fichier_wav.setframerate(sample_rate)
        fichier_wav.writeframes(pcm)
    return tampon.getvalue()


def _transcrire_audio(contenu_audio: bytes, nom_fichier: str, type_contenu: str) -> str:
    """Voix du client -> texte, via Whisper hébergé sur Groq (même clé que
    le chat)."""
    try:
        reponse = httpx.post(
            GROQ_TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            files={"file": (nom_fichier, contenu_audio, type_contenu)},
            data={"model": GROQ_WHISPER_MODEL, "language": "fr"},
            timeout=30.0,
        )
        reponse.raise_for_status()
        texte = reponse.json()["text"]
    except (httpx.HTTPError, KeyError) as erreur:
        raise ServiceIAIndisponibleError(str(erreur))

    if not texte or not texte.strip():
        raise ServiceIAIndisponibleError("Transcription vide.")
    return texte.strip()


def _synthetiser_voix(texte: str) -> bytes:
    """Réponse texte de JARVIS -> voix, via Gemini (réservé à cet usage,
    jamais utilisé pour le raisonnement financier lui-même)."""
    try:
        reponse = httpx.post(
            GEMINI_TTS_URL,
            params={"key": settings.GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": texte}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_TTS_VOICE}}
                    },
                },
            },
            timeout=30.0,
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        audio_base64 = donnees["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        pcm = base64.b64decode(audio_base64)
    except (httpx.HTTPError, KeyError, IndexError) as erreur:
        raise ServiceIAIndisponibleError(str(erreur))

    return _pcm_vers_wav(pcm)


def poser_question_vocale(
    db: Session, id_client: int, id_conversation: UUID, contenu_audio: bytes, nom_fichier: str, type_contenu: str
) -> Tuple[Message, Optional[bytes]]:
    """
    Voix -> texte -> même raisonnement financier que le chat écrit (aucune
    logique dupliquée) -> texte -> voix. Si la transcription échoue, rien
    n'est créé (on n'a même pas de question exploitable). Si seule la
    synthèse vocale finale échoue, la réponse texte reste renvoyée avec
    audio=None plutôt que de perdre un raisonnement déjà réussi et
    persisté — mieux vaut une réponse affichée sans voix qu'aucune réponse.
    """
    texte_transcrit = _transcrire_audio(contenu_audio, nom_fichier, type_contenu)
    message = poser_question(db, id_client, id_conversation, texte_transcrit, canal="VOCAL")

    try:
        audio_reponse = _synthetiser_voix(message.contenu)
    except ServiceIAIndisponibleError:
        return message, None

    return message, audio_reponse
