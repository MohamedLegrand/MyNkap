import base64
import io
import json
import secrets
import wave
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple
from uuid import UUID
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.budgets import service as budgets_service
from app.modules.comptes import service as comptes_service
from app.modules.comptes.schemas import CompteFinancierCreate
from app.modules.dettes import service as dettes_service
from app.modules.epargne import service as epargne_service
from app.modules.jarvis.models import ActionIA, Conversation, Message
from app.modules.transactions import service as transactions_service
from app.modules.transactions.schemas import TransactionCreate

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
- Tu peux PROPOSER des actions concrètes (créer une dépense/un revenu sur un compte existant, ou \
créer un nouveau compte) mais tu ne les exécutes JAMAIS toi-même : elles restent en attente \
jusqu'à ce que le client les confirme explicitement via un bouton dans l'application. N'invente \
jamais un id_compte ou id_categorie — utilise EXCLUSIVEMENT ceux listés ci-dessous. S'il manque \
une information essentielle (montant, quel compte, quelle catégorie) ou que le compte/la \
catégorie mentionné n'existe pas dans la liste, demande une clarification au lieu de proposer une \
action incomplète ou incorrecte.
- Si le client décrit plusieurs opérations dans un seul message (par exemple : "j'ai dépensé 2000 \
pour manger et 500 de taxi"), propose une action distincte pour chacune dans le tableau "actions".

Situation financière actuelle du client :
{contexte_financier}

{catalogue_comptes_categories}

Tu dois TOUJOURS répondre en JSON valide, avec exactement cette forme, sans aucun texte en dehors :
{{
  "contenu": "ta réponse en français, claire et concise",
  "necessite_clarification": true ou false,
  "options_suggerees": ["option 1", "option 2"] ou null si necessite_clarification est false,
  "peut_se_permettre": true, false ou null si la question ne porte pas sur un achat,
  "montant_suggere": nombre ou null,
  "conseil_supplementaire": "un conseil court" ou null,
  "actions": [
    {{"type": "CREER_TRANSACTION", "id_compte": 30, "id_categorie": 12, "montant": 2000, "type_transaction": "DEPENSE", "description": "Courses au marché"}},
    {{"type": "CREER_COMPTE", "nom": "Épargne vacances", "type_compte": "EPARGNE", "devise": "XAF", "solde_initial": 20000}}
  ]
}}
Le tableau "actions" est [] si tu ne proposes aucune action.
"""

# Une action proposée expire si elle n'est pas confirmée à temps — un
# "oui" tapé le lendemain sur un montant halluciné ou périmé ne doit
# jamais s'exécuter silencieusement.
DUREE_VALIDITE_ACTION = timedelta(minutes=30)
TYPES_COMPTE_VALIDES = {"MOBILE_MONEY", "BANCAIRE", "ESPECES", "EPARGNE"}
TYPES_TRANSACTION_VALIDES = {"DEPENSE", "REVENU"}


class ConversationIntrouvableError(Exception):
    """La conversation n'existe pas ou n'appartient pas au client."""


class ServiceIAIndisponibleError(Exception):
    """L'appel au fournisseur IA a échoué (réseau, clé invalide, quota, réponse invalide...)."""


class ActionIntrouvableError(Exception):
    """L'action n'existe pas, n'appartient pas au client, ou n'est plus en attente de confirmation."""


class ActionExpireeError(Exception):
    """Le délai de confirmation de cette action est dépassé — elle vient d'être annulée automatiquement."""


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


def _formatter_catalogue_pour_ia(comptes: list, categories: list) -> str:
    """
    Liste les comptes/catégories réels du client avec leur identifiant —
    seule source d'identifiants que JARVIS a le droit d'utiliser pour
    proposer une action (voir _valider_et_creer_actions, qui rejette tout
    id_compte/id_categorie ne figurant pas dans cette liste).
    """
    lignes = ["Comptes existants (id_compte : nom, type, solde) :"]
    if comptes:
        for compte in comptes:
            lignes.append(f"  - {compte.id_compte} : {compte.nom} ({compte.type}), {compte.solde} XAF")
    else:
        lignes.append("  - aucun compte pour l'instant")

    lignes.append("Catégories existantes (id_categorie : nom, type) :")
    categories_actives = [c for c in categories if c.est_actif]
    if categories_actives:
        for categorie in categories_actives:
            lignes.append(f"  - {categorie.id_categorie} : {categorie.nom} ({categorie.type})")
    else:
        lignes.append("  - aucune catégorie pour l'instant")

    return "\n".join(lignes)


def _valider_et_creer_actions(
    id_client: int, message: Message, actions_brutes: list, comptes: list, categories: list
) -> List[ActionIA]:
    """
    Convertit les actions proposées par le fournisseur IA en ActionIA
    EN_ATTENTE — ne les exécute jamais. Toute action référençant un
    id_compte/id_categorie halluciné (n'appartenant pas réellement au
    client) est silencieusement écartée : JARVIS ne peut pas se rattraper
    après coup sur un message déjà envoyé, mieux vaut ne rien proposer
    qu'une action incorrecte.
    """
    comptes_par_id = {compte.id_compte: compte for compte in comptes}
    categories_par_id = {c.id_categorie: c for c in categories if c.est_actif}
    date_expiration = datetime.utcnow() + DUREE_VALIDITE_ACTION

    actions: List[ActionIA] = []
    for brute in actions_brutes:
        if not isinstance(brute, dict):
            continue
        type_action = brute.get("type")

        if type_action == "CREER_TRANSACTION":
            compte = comptes_par_id.get(brute.get("id_compte"))
            categorie = categories_par_id.get(brute.get("id_categorie"))
            type_transaction = brute.get("type_transaction")
            if compte is None or categorie is None or type_transaction not in TYPES_TRANSACTION_VALIDES:
                continue
            try:
                montant = Decimal(str(brute.get("montant")))
            except (InvalidOperation, TypeError):
                continue
            if montant <= 0:
                continue

            description = brute.get("description")
            libelle_type = "Dépense" if type_transaction == "DEPENSE" else "Revenu"
            resume = f"{libelle_type} de {montant} XAF ({categorie.nom}) sur {compte.nom}"
            donnees_cible = json.dumps({
                "id_compte": compte.id_compte,
                "id_categorie": categorie.id_categorie,
                "montant": str(montant),
                "type_transaction": type_transaction,
                "description": description,
            })
            actions.append(ActionIA(
                id_client=id_client, id_message=message.id_message, type_action="CREER_TRANSACTION",
                donnees_cible=donnees_cible, resume=resume, confirmation_token=secrets.token_urlsafe(24),
                statut="EN_ATTENTE", date_expiration=date_expiration,
            ))

        elif type_action == "CREER_COMPTE":
            nom = brute.get("nom")
            type_compte = brute.get("type_compte")
            if not nom or type_compte not in TYPES_COMPTE_VALIDES:
                continue
            try:
                solde_initial = Decimal(str(brute.get("solde_initial") or 0))
            except InvalidOperation:
                continue
            if solde_initial < 0:
                continue
            devise = brute.get("devise") or "XAF"

            resume = f"Nouveau compte « {nom} » ({type_compte})"
            if solde_initial > 0:
                resume += f" avec un dépôt initial de {solde_initial} {devise}"
            donnees_cible = json.dumps({
                "nom": nom, "type_compte": type_compte, "devise": devise, "solde_initial": str(solde_initial),
            })
            actions.append(ActionIA(
                id_client=id_client, id_message=message.id_message, type_action="CREER_COMPTE",
                donnees_cible=donnees_cible, resume=resume, confirmation_token=secrets.token_urlsafe(24),
                statut="EN_ATTENTE", date_expiration=date_expiration,
            ))

    return actions


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
    comptes = comptes_service.lister_comptes(db, id_client)
    categories = budgets_service.obtenir_categories(db, id_client)
    catalogue = _formatter_catalogue_pour_ia(comptes, categories)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        contexte_financier=contexte_financier, catalogue_comptes_categories=catalogue
    )

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
    db.flush()  # pour obtenir id_message avant de créer les ActionIA liées

    actions_proposees = _valider_et_creer_actions(
        id_client, reponse, donnees.get("actions") or [], comptes, categories
    )
    db.add_all(actions_proposees)

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


# --- Confirmation des actions proposées par JARVIS ---

def _obtenir_action_en_attente(db: Session, id_client: int, id_action: UUID) -> ActionIA:
    action = (
        db.query(ActionIA)
        .filter(ActionIA.id_action == id_action, ActionIA.id_client == id_client)
        .first()
    )
    if action is None or action.statut != "EN_ATTENTE":
        raise ActionIntrouvableError()
    return action


def confirmer_action(db: Session, id_client: int, id_action: UUID) -> ActionIA:
    """
    Exécute réellement l'action proposée par JARVIS, en passant
    systématiquement par les vraies fonctions de service des modules
    cibles (jamais de logique dupliquée) — tous les garde-fous existants
    s'appliquent donc automatiquement (solde jamais négatif, détection de
    transaction suspecte...). Si le compte/la catégorie a été désactivé ou
    le solde est devenu insuffisant depuis la proposition, l'exception du
    module cible remonte telle quelle et l'action reste EN_ATTENTE — le
    client peut réessayer plus tard, jusqu'à expiration.
    """
    action = _obtenir_action_en_attente(db, id_client, id_action)

    if action.date_expiration is not None and datetime.utcnow() > action.date_expiration:
        action.statut = "ANNULE"
        db.commit()
        raise ActionExpireeError()

    donnees = json.loads(action.donnees_cible)

    if action.type_action == "CREER_TRANSACTION":
        transactions_service.enregistrer_transaction(
            db, id_client,
            TransactionCreate(
                id_compte=donnees["id_compte"],
                id_categorie=donnees["id_categorie"],
                montant=Decimal(donnees["montant"]),
                type=donnees["type_transaction"],
                description=donnees.get("description"),
            ),
        )
    elif action.type_action == "CREER_COMPTE":
        comptes_service.creer_compte(
            db, id_client,
            CompteFinancierCreate(
                nom=donnees["nom"],
                type=donnees["type_compte"],
                devise=donnees.get("devise", "XAF"),
                solde_initial=Decimal(donnees["solde_initial"]),
            ),
        )

    action.statut = "EXECUTE"
    db.commit()
    db.refresh(action)
    return action


def annuler_action(db: Session, id_client: int, id_action: UUID) -> ActionIA:
    action = _obtenir_action_en_attente(db, id_client, id_action)
    action.statut = "ANNULE"
    db.commit()
    db.refresh(action)
    return action
