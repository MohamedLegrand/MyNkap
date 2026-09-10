"""
Client HTTP de l'API « Encaissement par carte bancaire » de HR-Skills Pay
(E-NKAP / Flocash).

Le SDK Python `hrpay` ne couvre QUE le Cash-In Mobile Money. L'encaissement
carte est une surface REST distincte (page de paiement hébergée : le client
est redirigé vers `checkout_url`, saisit sa carte chez Flocash, puis revient
sur `return_url`/`cancel_url`). Le rebond navigateur n'est jamais la source
de vérité du statut : on relit `GET /payments/card/:reference` (polling),
exactement comme pour le Mobile Money.

Ce module ne fait QUE l'appel réseau et la traduction des réponses/erreurs
HTTP en objets/exceptions Python. Toute la logique métier (création de la
ligne en base, crédit du compte, gross-up de la commission...) vit dans les
services `recharges` / `plans`, qui enveloppent ces fonctions dans des
helpers `_creer_paiement_carte` / `_lire_paiement_carte` mockés en test —
aucun test ne doit jamais déclencher un vrai appel.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Chemin commun aux deux opérations (création + lecture), ajouté à
# settings.hrpay_card_api_base (qui inclut déjà /sandbox le cas échéant).
_CHEMIN = "/api/v1/payments/card"

# Délai généreux : l'appel de création peut déclencher côté HR-Skills Pay un
# aller-retour vers E-NKAP avant de répondre.
_TIMEOUT = httpx.Timeout(20.0)


class CarteError(Exception):
    """Base de toutes les erreurs de ce module (pour un `except` unique)."""


class CartePaiementRefuseError(CarteError):
    """
    La demande est rejetée à cause des données fournies (montant invalide
    ou au-delà du plafond, blocage anti-fraude) — le client peut corriger
    et réessayer. Équivalent carte de recharges.PaiementRefuseError.
    """


class ServiceCarteIndisponibleError(CarteError):
    """
    L'appel a échoué pour une raison imputable à HR-Skills Pay / E-NKAP /
    au réseau (5xx, timeout, réponse illisible). Équivalent carte de
    recharges.ServicePaiementIndisponibleError.
    """


class CartePaiementIntrouvableError(CarteError):
    """La référence n'existe pas pour ce marchand/environnement (404)."""


@dataclass(frozen=True)
class PaiementCarteCree:
    """Résultat de la création d'un paiement carte."""
    reference: str
    # None quand le paiement est gelé en revue anti-fraude (score 51-75) ou
    # que E-NKAP est momentanément indisponible avec rattrapage en cours
    # (deux cas de réponse 202). Le paiement reste PENDING : on ne redirige
    # pas le client, le frontend affiche « en attente » et on poll le statut.
    checkout_url: Optional[str]
    statut: str


@dataclass(frozen=True)
class StatutPaiementCarte:
    """Résultat de la relecture d'un paiement carte."""
    reference: str
    statut: str  # PENDING, AUTHORIZED, CAPTURED, SETTLED, REFUNDED, FAILED, CANCELED
    checkout_url: Optional[str]
    frais: Decimal
    montant_net: Decimal
    fraud_review_status: str  # NONE, PENDING_REVIEW, CLEARED, REJECTED


def mapper_statut(statut_carte: str) -> str:
    """
    Traduit le cycle de vie carte E-NKAP vers les 3 états internes utilisés
    partout dans MyNkap pour un paiement asynchrone (PENDING/SUCCESS/FAILED)
    — mêmes états que le Mobile Money, pour que
    `verifier_*_en_attente` reste un seul chemin de code.

    - CAPTURED / SETTLED       -> SUCCESS (fonds encaissés)
    - FAILED / CANCELED        -> FAILED
    - REFUNDED                 -> FAILED (un paiement encore en attente qui
                                  finit remboursé n'aboutira pas ; les
                                  chargebacks post-succès sont hors périmètre)
    - PENDING / AUTHORIZED     -> PENDING (AUTHORIZED est transitoire : E-NKAP
                                  pose AUTHORIZED puis CAPTURED dans la foulée)
    """
    if statut_carte in ("CAPTURED", "SETTLED"):
        return "SUCCESS"
    if statut_carte in ("FAILED", "CANCELED", "REFUNDED"):
        return "FAILED"
    return "PENDING"


def _headers(idempotency_key: Optional[str] = None) -> dict:
    """
    En-têtes d'authentification. Les clés sont transmises telles quelles
    (valeur copiée depuis le tableau de bord HR-Skills Pay). Si la sandbox
    exige explicitement une valeur base64, c'est le seul endroit à changer.
    """
    entetes = {
        "Authorization": f"Bearer {settings.HRPAY_PUBLIC_KEY or ''}",
        "X-API-Secret": settings.HRPAY_SECRET_KEY or "",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        entetes["Idempotency-Key"] = idempotency_key
    return entetes


def _url() -> str:
    return f"{settings.hrpay_card_api_base}{_CHEMIN}"


def creer_paiement(
    *,
    montant: Decimal,
    devise: str,
    description: str,
    return_url: str,
    cancel_url: str,
    client_nom: str,
    client_email: str,
    client_phone: str,
    client_ip: Optional[str],
    idempotency_key: str,
    lang: str = "fr",
) -> PaiementCarteCree:
    """
    POST /api/v1/payments/card — crée la commande carte. `idempotency_key`
    garantit qu'un retry réseau ne crée pas deux paiements.

    Réponses gérées :
    - 201 : checkout_url rempli, statut PENDING (cas nominal)
    - 202 : checkout_url null, statut PENDING (revue anti-fraude OU E-NKAP
            indisponible avec rattrapage) — non bloquant, on poll ensuite
    - 403 FRAUD_BLOCKED / 422 montant : -> CartePaiementRefuseError
    - 4xx/5xx/timeout/réponse illisible : -> ServiceCarteIndisponibleError
    """
    corps = {
        "amount": float(montant),
        "currency": devise,
        "description": description,
        "lang": lang,
        "return_url": return_url,
        "cancel_url": cancel_url,
        "customer": {
            "name": client_nom,
            "email": client_email,
            "phone": client_phone,
            "ip_address": client_ip or "",
        },
    }
    try:
        reponse = httpx.post(_url(), json=corps, headers=_headers(idempotency_key), timeout=_TIMEOUT)
    except httpx.HTTPError as erreur:
        logger.warning("Échec réseau création paiement carte : %s", erreur)
        raise ServiceCarteIndisponibleError(str(erreur))

    if reponse.status_code in (200, 201, 202):
        données = _extraire_data(reponse)
        return PaiementCarteCree(
            reference=str(données.get("reference") or ""),
            checkout_url=données.get("checkout_url") or None,
            statut=str(données.get("status") or "PENDING"),
        )

    code_metier = _code_erreur(reponse)
    if reponse.status_code in (403, 422):
        logger.warning("Paiement carte refusé : http=%s code=%s", reponse.status_code, code_metier)
        raise CartePaiementRefuseError(_message_refus(code_metier))

    logger.warning(
        "Échec HR-Skills Pay (création carte) : http=%s code=%s corps=%s",
        reponse.status_code, code_metier, reponse.text[:500],
    )
    raise ServiceCarteIndisponibleError(f"HR-Skills Pay a répondu {reponse.status_code} ({code_metier}).")


def lire_paiement(reference: str) -> StatutPaiementCarte:
    """
    GET /api/v1/payments/card/:reference — relit l'état ; côté HR-Skills Pay
    ça revérifie systématiquement auprès d'E-NKAP tant que le paiement est
    PENDING (jamais un simple miroir d'un webhook).
    """
    try:
        reponse = httpx.get(
            f"{_url()}/{reference}", headers=_headers(), timeout=_TIMEOUT
        )
    except httpx.HTTPError as erreur:
        logger.warning("Échec réseau lecture paiement carte %s : %s", reference, erreur)
        raise ServiceCarteIndisponibleError(str(erreur))

    if reponse.status_code == 404:
        raise CartePaiementIntrouvableError(reference)
    if reponse.status_code != 200:
        logger.warning(
            "Échec HR-Skills Pay (lecture carte %s) : http=%s corps=%s",
            reference, reponse.status_code, reponse.text[:500],
        )
        raise ServiceCarteIndisponibleError(f"HR-Skills Pay a répondu {reponse.status_code}.")

    données = _extraire_data(reponse)
    return StatutPaiementCarte(
        reference=str(données.get("reference") or reference),
        statut=str(données.get("status") or "PENDING"),
        checkout_url=données.get("checkout_url") or None,
        frais=_to_decimal(données.get("fee")),
        montant_net=_to_decimal(données.get("net_amount")),
        fraud_review_status=str(données.get("fraud_review_status") or "NONE"),
    )


def _extraire_data(reponse: httpx.Response) -> dict:
    try:
        charge = reponse.json()
    except ValueError:
        raise ServiceCarteIndisponibleError("Réponse HR-Skills Pay illisible (JSON attendu).")
    données = charge.get("data") if isinstance(charge, dict) else None
    if not isinstance(données, dict):
        raise ServiceCarteIndisponibleError("Réponse HR-Skills Pay inexploitable (champ 'data' absent).")
    return données


def _code_erreur(reponse: httpx.Response) -> str:
    try:
        charge = reponse.json()
    except ValueError:
        return ""
    if isinstance(charge, dict):
        return str(charge.get("code") or charge.get("error_code") or "")
    return ""


def _message_refus(code_metier: str) -> str:
    return {
        "INVALID_AMOUNT": "Le montant du paiement est invalide.",
        "AMOUNT_EXCEEDS_LIMIT": "Le montant dépasse le plafond autorisé par opération.",
        "FRAUD_BLOCKED": "Paiement refusé par le contrôle anti-fraude.",
    }.get(code_metier, "Paiement par carte refusé.")


def _to_decimal(valeur) -> Decimal:
    if valeur is None:
        return Decimal("0")
    try:
        return Decimal(str(valeur))
    except (ValueError, ArithmeticError):
        return Decimal("0")
