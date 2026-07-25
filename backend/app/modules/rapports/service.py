import os
import socket
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from xhtml2pdf import pisa

from app.core.config import settings
from app.modules.analyse import service as analyse_service
from app.modules.budgets import service as budgets_service
from app.modules.budgets.models import Categorie
from app.modules.dettes import service as dettes_service
from app.modules.epargne import service as epargne_service
from app.modules.plans import service as plans_service
from app.modules.rapports.models import Rapport
from app.modules.transactions.models import Transaction

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
LOGO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "static", "logo.jpg")
).replace("\\", "/")

_environnement_jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


class TypeRapportInvalideError(Exception):
    """Le type de rapport demandé ne fait pas partie du catalogue."""


class FonctionnaliteNonAutoriseeError(Exception):
    """Le plan actif du client ne donne pas accès à ce type de rapport."""


def _fmt(montant: Decimal) -> str:
    return f"{montant:,.0f}".replace(",", " ")


# --- Agrégation des données par type de rapport ---

def _donnees_releve_transactions(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    annulees = (
        db.query(Transaction.id_transaction_annulee)
        .filter(Transaction.type == "ANNULATION", Transaction.id_transaction_annulee.isnot(None))
    ).scalar_subquery()

    lignes = (
        db.query(Transaction, Categorie.nom)
        .outerjoin(Categorie, Transaction.id_categorie == Categorie.id_categorie)
        .filter(
            Transaction.id_client == id_client,
            Transaction.type.in_(["DEPENSE", "REVENU"]),
            Transaction.date >= periode_debut,
            Transaction.date <= periode_fin,
            Transaction.id_transaction.notin_(annulees),
        )
        .order_by(Transaction.date.asc())
        .all()
    )

    transactions = []
    total_depenses = Decimal("0")
    total_revenus = Decimal("0")
    for transaction, nom_categorie in lignes:
        transactions.append({
            "date": transaction.date.strftime("%d/%m/%Y"),
            "categorie": nom_categorie or "—",
            "type": transaction.type,
            "description": transaction.description,
            "montant": _fmt(transaction.montant),
        })
        if transaction.type == "DEPENSE":
            total_depenses += transaction.montant
        else:
            total_revenus += transaction.montant

    solde_net = total_revenus - total_depenses
    return {
        "transactions": transactions,
        "total_depenses": _fmt(total_depenses),
        "total_revenus": _fmt(total_revenus),
        "solde_net": _fmt(solde_net),
        "solde_net_positif": solde_net >= 0,
    }


def _donnees_bilan_budgetaire(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    budgets = []
    for budget, valeurs in budgets_service.lister_budgets(db, id_client):
        if budget.mois != periode_debut.month or budget.annee != periode_debut.year:
            continue
        budgets.append({
            "categorie": budget.categorie.nom,
            "limite": _fmt(budget.montant_limite),
            "depense": _fmt(valeurs["montant_depense"]),
            "restant": _fmt(valeurs["montant_restant"]),
            "restant_negatif": valeurs["montant_restant"] < 0,
            "pourcentage": round(valeurs["pourcentage_utilise"], 1),
            "depasse": valeurs["est_depasse"],
        })
    return {"budgets": budgets}


def _donnees_dettes_epargne(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    def _vers_dict(dette):
        return {
            "nom": dette.nom,
            "montant_total": _fmt(dette.montant_total),
            "montant_rembourse": _fmt(dette.montant_rembourse),
            "montant_restant": _fmt(dette.get_montant_restant()),
            "echeance": dette.date_echeance.strftime("%d/%m/%Y") if dette.date_echeance else None,
            "statut": dette.statut,
        }

    objectifs = []
    for objectif in epargne_service.lister_objectifs(db, id_client):
        valeurs = epargne_service.calculer_valeurs_objectif(objectif)
        objectifs.append({
            "nom": objectif.nom,
            "montant_cible": _fmt(objectif.montant_cible),
            "montant_actuel": _fmt(valeurs["montant_actuel"]),
            "pourcentage": round(valeurs["pourcentage_atteint"], 1),
            "statut": objectif.statut,
        })

    return {
        "dettes": [_vers_dict(d) for d in dettes_service.lister_dettes(db, id_client, "DETTE")],
        "creances": [_vers_dict(c) for c in dettes_service.lister_dettes(db, id_client, "CREANCE")],
        "objectifs": objectifs,
    }


def _donnees_bilan_financier(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    habitudes = analyse_service.calculer_habitudes(db, id_client, periode_debut, periode_fin)
    tendances_brut = analyse_service.calculer_tendances(db, id_client, periode_debut, periode_fin)
    comparaison_brut = analyse_service.calculer_comparaison(db, id_client, periode_debut, periode_fin)
    comportement = analyse_service.calculer_comportement(db, id_client, periode_debut, periode_fin)

    repartition = [
        {"categorie": r["categorie"], "montant": _fmt(Decimal(r["montant"])), "pourcentage": r["pourcentage"]}
        for r in habitudes["repartition"]
    ]

    tendances = []
    for t in tendances_brut["tendances"]:
        variation = t["variation_pourcentage"]
        tendances.append({
            "categorie": t["categorie"],
            "montant_periode": _fmt(Decimal(t["montant_periode"])),
            "moyenne": _fmt(Decimal(t["moyenne_glissante_3_mois"])),
            "variation": f"{variation:+.1f}%" if variation is not None else "—",
            "hausse": (variation or 0) > 0,
        })

    return {
        "score_financier": analyse_service.calculer_score_financier(db, id_client, periode_debut, periode_fin),
        "total_depenses": _fmt(Decimal(habitudes["total_depenses"])),
        "repartition": repartition,
        "tendances": tendances,
        "comparaison": {
            "depenses_actuelles": _fmt(Decimal(comparaison_brut["depenses_periode_actuelle"])),
            "depenses_precedentes": _fmt(Decimal(comparaison_brut["depenses_periode_precedente"])),
            "revenus_actuelles": _fmt(Decimal(comparaison_brut["revenus_periode_actuelle"])),
            "revenus_precedentes": _fmt(Decimal(comparaison_brut["revenus_periode_precedente"])),
        },
        "comportement": comportement,
    }


def _donnees_predictions(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    def _formater(prediction: dict) -> dict:
        montant = prediction["montant_predit"]
        confiance = prediction["niveau_confiance"]
        return {
            "montant": _fmt(montant) if montant is not None else "—",
            "confiance": round(confiance * 100) if confiance is not None else "—",
            "recommandation": prediction["recommandations"],
        }

    return {
        "depenses_futures": _formater(
            analyse_service.predire_depenses_futures(db, id_client, periode_debut, periode_fin)
        ),
        "risque_budgetaire": _formater(
            analyse_service.predire_risque_budgetaire(db, id_client, periode_debut, periode_fin)
        ),
        "capacite_epargne": _formater(
            analyse_service.predire_capacite_epargne(db, id_client, periode_debut, periode_fin)
        ),
    }


# --- Catalogue : type -> fonctionnalité requise, template, données, titre ---
CATALOGUE_RAPPORTS = {
    "RELEVE_TRANSACTIONS": {
        "acces": None, "template": "releve_transactions.html",
        "donnees": _donnees_releve_transactions, "titre": "Relevé de transactions",
    },
    "BILAN_BUDGETAIRE": {
        "acces": None, "template": "bilan_budgetaire.html",
        "donnees": _donnees_bilan_budgetaire, "titre": "Bilan budgétaire",
    },
    "DETTES_EPARGNE": {
        "acces": "acces_dettes", "template": "dettes_epargne.html",
        "donnees": _donnees_dettes_epargne, "titre": "Dettes & Épargne",
    },
    "BILAN_FINANCIER": {
        "acces": "acces_analyse", "template": "bilan_financier.html",
        "donnees": _donnees_bilan_financier, "titre": "Bilan financier",
    },
    "PREDICTIONS": {
        "acces": "acces_analyse", "template": "predictions.html",
        "donnees": _donnees_predictions, "titre": "Prédictions financières",
    },
}


# --- Points d'entrée ---

def demander_rapport(db: Session, id_client: int, type_rapport: str, periode_debut: date, periode_fin: date) -> Rapport:
    """
    Crée le Rapport en EN_COURS et le confie à la tâche de fond
    generer_rapport (voir worker.tasks) — jamais généré dans la requête
    HTTP elle-même, pour ne jamais bloquer sur le rendu PDF.
    """
    if type_rapport not in CATALOGUE_RAPPORTS:
        raise TypeRapportInvalideError()

    acces_requis = CATALOGUE_RAPPORTS[type_rapport]["acces"]
    if acces_requis is not None:
        abonnement = plans_service.obtenir_abonnement_actif(db, id_client)
        if not getattr(abonnement.plan, acces_requis, False):
            raise FonctionnaliteNonAutoriseeError()

    rapport = Rapport(
        id_client=id_client,
        type=type_rapport,
        periode_debut=periode_debut,
        periode_fin=periode_fin,
        statut="EN_COURS",
    )
    db.add(rapport)
    db.commit()
    db.refresh(rapport)
    return rapport


def generer_rapport(db: Session, id_rapport: int) -> Optional[Rapport]:
    """
    Génère réellement le fichier PDF. Capture large et volontaire :
    n'importe quel échec (données, rendu, écriture disque) doit marquer le
    rapport ERREUR plutôt que de faire planter la tâche de fond — un
    rapport cassé pour un client ne doit jamais affecter les autres.
    """
    rapport = db.query(Rapport).filter(Rapport.id_rapport == id_rapport).first()
    if rapport is None:
        return None

    config = CATALOGUE_RAPPORTS[rapport.type]
    try:
        donnees = config["donnees"](db, rapport.id_client, rapport.periode_debut, rapport.periode_fin)
        contexte = {
            "logo_path": LOGO_PATH,
            "titre": config["titre"],
            "periode_debut": rapport.periode_debut.strftime("%d/%m/%Y"),
            "periode_fin": rapport.periode_fin.strftime("%d/%m/%Y"),
            "date_generation": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
            **donnees,
        }
        html = _environnement_jinja.get_template(config["template"]).render(**contexte)

        os.makedirs(settings.RAPPORTS_DOSSIER, exist_ok=True)
        chemin = os.path.join(settings.RAPPORTS_DOSSIER, f"rapport_{rapport.id_rapport}.pdf")
        with open(chemin, "wb") as fichier:
            resultat = pisa.CreatePDF(html, dest=fichier)
        if resultat.err:
            raise RuntimeError(f"{resultat.err} erreur(s) de rendu PDF")

        rapport.chemin_fichier = chemin
        rapport.taille = os.path.getsize(chemin)
        rapport.statut = "GENERE"
    except Exception:
        rapport.statut = "ERREUR"

    db.commit()
    db.refresh(rapport)
    return rapport


def _broker_disponible() -> bool:
    """
    Vérification socket rapide (timeout court) avant tout envoi à Celery.
    kombu/Celery peuvent bloquer plusieurs dizaines de secondes en retry
    silencieux si Redis n'est pas démarré — inacceptable dans une requête
    HTTP. Un simple connect() qui échoue instantanément (connexion
    refusée) évite ce piège sans jamais dépendre du comportement interne
    du client Celery.
    """
    url = urlparse(settings.REDIS_URL)
    try:
        with socket.create_connection((url.hostname, url.port or 6379), timeout=0.3):
            return True
    except OSError:
        return False


def dispatcher_generation(id_rapport: int) -> None:
    """
    Envoie la génération à la tâche de fond si le broker est joignable ;
    sinon, laisse le rapport en EN_COURS plutôt que de faire échouer la
    requête HTTP qui vient de le créer.
    """
    if not _broker_disponible():
        return

    from app.worker.tasks import generer_rapport_tache

    try:
        generer_rapport_tache.apply_async(args=[id_rapport], retry=False)
    except Exception:
        pass


def obtenir_rapport_du_client(db: Session, id_rapport: int, id_client: int) -> Optional[Rapport]:
    return (
        db.query(Rapport)
        .filter(Rapport.id_rapport == id_rapport, Rapport.id_client == id_client)
        .first()
    )


def lister_rapports(db: Session, id_client: int) -> List[Rapport]:
    return (
        db.query(Rapport)
        .filter(Rapport.id_client == id_client)
        .order_by(Rapport.date_generation.desc())
        .all()
    )
