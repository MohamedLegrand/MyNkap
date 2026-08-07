import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.analyse.models import AnalyseFinanciere, Prediction
from app.modules.auth.models import Client
from app.modules.budgets import service as budgets_service
from app.modules.budgets.models import Categorie
from app.modules.comptes import service as comptes_service
from app.modules.dettes import service as dettes_service
from app.modules.epargne.models import ObjectifEpargne
from app.modules.transactions.models import Transaction, Transfert

# Nombre de mois utilisés comme base de comparaison pour les tendances et
# les prédictions — cohérent avec la fenêtre de 30 jours déjà utilisée
# pour la détection de transactions suspectes, généralisé sur plusieurs mois.
NB_MOIS_MOYENNE_GLISSANTE = 3


class TypeAnalyseInvalideError(Exception):
    """Le type d'analyse demandé ne fait pas partie du catalogue connu."""


class TypePredictionInvalideError(Exception):
    """Le type de prédiction demandé ne fait pas partie du catalogue connu."""


# --- Périodes ---

def _limites_mois(annee: int, mois: int) -> Tuple[date, date]:
    debut = date(annee, mois, 1)
    dernier_jour = calendar.monthrange(annee, mois)[1]
    return debut, date(annee, mois, dernier_jour)


def _mois_precedents(reference: date, nb_mois: int) -> List[Tuple[date, date]]:
    """Les nb_mois mois civils qui précèdent (hors) le mois de `reference`,
    toujours des mois pleins — jamais un mois en cours, pour ne pas biaiser
    une moyenne avec des données partielles."""
    resultats = []
    annee, mois = reference.year, reference.month
    for _ in range(nb_mois):
        mois -= 1
        if mois == 0:
            mois, annee = 12, annee - 1
        resultats.append(_limites_mois(annee, mois))
    return resultats


def _mois_suivant(reference: date) -> Tuple[date, date]:
    annee, mois = reference.year, reference.month + 1
    if mois > 12:
        mois, annee = 1, annee + 1
    return _limites_mois(annee, mois)


# --- Agrégations de base ---

def _sous_requete_transactions_annulees(db: Session):
    return (
        db.query(Transaction.id_transaction_annulee)
        .filter(Transaction.type == "ANNULATION", Transaction.id_transaction_annulee.isnot(None))
    ).scalar_subquery()


def _total_transactions(db: Session, id_client: int, type_transaction: str, date_debut: date, date_fin: date) -> Decimal:
    annulees = _sous_requete_transactions_annulees(db)
    total = db.query(func.sum(Transaction.montant)).filter(
        Transaction.id_client == id_client,
        Transaction.type == type_transaction,
        Transaction.date >= date_debut,
        Transaction.date <= date_fin,
        Transaction.id_transaction.notin_(annulees),
    ).scalar()
    return Decimal(str(total)) if total is not None else Decimal("0")


def _moyenne_mensuelle(db: Session, id_client: int, type_transaction: str, reference: date, nb_mois: int = NB_MOIS_MOYENNE_GLISSANTE) -> Decimal:
    """Moyenne mensuelle sur les nb_mois derniers mois PLEINS avant `reference`
    (jamais le mois en cours de `reference`, même quand reference == aujourd'hui)."""
    periodes = _mois_precedents(reference, nb_mois)
    total = sum((_total_transactions(db, id_client, type_transaction, d, f) for d, f in periodes), Decimal("0"))
    # Quantize immédiatement : une division Decimal non arrondie peut produire
    # un développement décimal interminable, illisible une fois interpolé
    # dans un texte de recommandation ou affiché tel quel côté client.
    return (total / nb_mois).quantize(Decimal("0.01")) if nb_mois else Decimal("0")


def _depenses_par_categorie(db: Session, id_client: int, date_debut: date, date_fin: date) -> Dict[str, Decimal]:
    annulees = _sous_requete_transactions_annulees(db)
    lignes = (
        db.query(Categorie.nom, func.sum(Transaction.montant))
        .join(Transaction, Transaction.id_categorie == Categorie.id_categorie)
        .filter(
            Transaction.id_client == id_client,
            Transaction.type == "DEPENSE",
            Transaction.date >= date_debut,
            Transaction.date <= date_fin,
            Transaction.id_transaction.notin_(annulees),
        )
        .group_by(Categorie.nom)
        .all()
    )
    return {nom: Decimal(str(montant)) for nom, montant in lignes}


def _depenses_moyennes_par_categorie(db: Session, id_client: int, reference: date, nb_mois: int = NB_MOIS_MOYENNE_GLISSANTE) -> Dict[str, Decimal]:
    periodes = _mois_precedents(reference, nb_mois)
    totaux: Dict[str, Decimal] = {}
    for debut, fin in periodes:
        for nom, montant in _depenses_par_categorie(db, id_client, debut, fin).items():
            totaux[nom] = totaux.get(nom, Decimal("0")) + montant
    return {nom: total / nb_mois for nom, total in totaux.items()}


def _budgets_de_la_periode(db: Session, id_client: int, periode_debut: date) -> List[Tuple]:
    """
    Budget est stocké par (mois, annee) — lister_budgets() renvoie TOUS les
    budgets actifs du client, tous mois confondus. On ne garde ici que
    ceux dont le (mois, annee) correspond réellement à la période
    analysée, sinon un budget de janvier polluerait le score de juillet.
    """
    tous = budgets_service.lister_budgets(db, id_client)
    return [
        (budget, valeurs)
        for budget, valeurs in tous
        if budget.mois == periode_debut.month and budget.annee == periode_debut.year
    ]


def _total_epargne_alimentee(db: Session, id_client: int, date_debut: date, date_fin: date) -> Decimal:
    comptes_epargne = db.query(ObjectifEpargne.id_compte_epargne).filter(ObjectifEpargne.id_client == id_client)
    total = db.query(func.sum(Transfert.montant)).filter(
        Transfert.id_client == id_client,
        Transfert.id_compte_destination.in_(comptes_epargne.scalar_subquery()),
        Transfert.date >= date_debut,
        Transfert.date <= date_fin,
    ).scalar()
    return Decimal(str(total)) if total is not None else Decimal("0")


# --- Score financier (0-100), 4 composantes à 25 points ---

def calculer_score_financier(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> float:
    # 1. Respect des budgets : pas de budget actif = neutre (score plein),
    # ce n'est pas au client de créer des budgets pour être bien noté.
    budgets = _budgets_de_la_periode(db, id_client, periode_debut)
    if not budgets:
        score_budgets = 25.0
    else:
        respectes = sum(1 for _, valeurs in budgets if not valeurs["est_depasse"])
        score_budgets = 25.0 * respectes / len(budgets)

    # 2. Taux d'épargne : sans revenu sur la période, impossible de juger
    # équitablement un taux d'épargne — score 0 plutôt que de fausser la
    # moyenne avec une division par zéro déguisée en "score parfait".
    revenus = _total_transactions(db, id_client, "REVENU", periode_debut, periode_fin)
    epargne = _total_epargne_alimentee(db, id_client, periode_debut, periode_fin)
    if revenus <= 0:
        score_epargne = 0.0
    else:
        taux = epargne / revenus
        score_epargne = min(25.0, float(taux / Decimal("0.20")) * 25.0)

    # 3. Maîtrise de l'endettement : proportion du patrimoine net absorbée
    # par les dettes restantes.
    dettes_actives = [d for d in dettes_service.lister_dettes(db, id_client, "DETTE") if d.statut != "SOLDE"]
    total_dettes = sum((d.get_montant_restant() for d in dettes_actives), Decimal("0"))
    if total_dettes <= 0:
        score_endettement = 25.0
    else:
        patrimoine_net = comptes_service.calculer_patrimoine_net(db, id_client)
        if patrimoine_net <= 0:
            score_endettement = 0.0
        else:
            ratio = min(total_dettes / patrimoine_net, Decimal("1"))
            score_endettement = 25.0 * (1 - float(ratio))

    # 4. Absence d'incidents : -5 points par transaction suspecte confirmée
    # ou non encore levée sur la période, plancher à 0.
    nb_suspectes = db.query(Transaction).filter(
        Transaction.id_client == id_client,
        Transaction.est_suspecte.is_(True),
        Transaction.date >= periode_debut,
        Transaction.date <= periode_fin,
    ).count()
    score_incidents = max(0.0, 25.0 - nb_suspectes * 5.0)

    return round(score_budgets + score_epargne + score_endettement + score_incidents, 1)


# --- Analyse : HABITUDES, TENDANCES, COMPARAISON, COMPORTEMENT ---

def calculer_habitudes(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    depenses = _depenses_par_categorie(db, id_client, periode_debut, periode_fin)
    total = sum(depenses.values(), Decimal("0"))
    repartition = sorted(
        (
            {
                "categorie": nom,
                "montant": str(montant),
                "pourcentage": round(float(montant / total * 100), 1) if total > 0 else 0.0,
            }
            for nom, montant in depenses.items()
        ),
        key=lambda ligne: -ligne["pourcentage"],
    )
    return {"total_depenses": str(total), "repartition": repartition}


def calculer_tendances(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    depenses_periode = _depenses_par_categorie(db, id_client, periode_debut, periode_fin)
    moyennes = _depenses_moyennes_par_categorie(db, id_client, periode_debut)
    categories = sorted(set(depenses_periode) | set(moyennes))

    tendances = []
    for nom in categories:
        montant = depenses_periode.get(nom, Decimal("0"))
        moyenne = moyennes.get(nom, Decimal("0"))
        variation = round(float((montant - moyenne) / moyenne * 100), 1) if moyenne > 0 else None
        tendances.append({
            "categorie": nom,
            "montant_periode": str(montant),
            "moyenne_glissante_3_mois": str(moyenne),
            "variation_pourcentage": variation,
        })
    return {"tendances": tendances}


def calculer_comparaison(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    jours = (periode_fin - periode_debut).days
    debut_precedente = periode_debut - timedelta(days=jours + 1)
    fin_precedente = periode_debut - timedelta(days=1)

    return {
        "depenses_periode_actuelle": str(_total_transactions(db, id_client, "DEPENSE", periode_debut, periode_fin)),
        "depenses_periode_precedente": str(_total_transactions(db, id_client, "DEPENSE", debut_precedente, fin_precedente)),
        "revenus_periode_actuelle": str(_total_transactions(db, id_client, "REVENU", periode_debut, periode_fin)),
        "revenus_periode_precedente": str(_total_transactions(db, id_client, "REVENU", debut_precedente, fin_precedente)),
    }


def calculer_comportement(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    nb_suspectes = db.query(Transaction).filter(
        Transaction.id_client == id_client,
        Transaction.est_suspecte.is_(True),
        Transaction.date >= periode_debut,
        Transaction.date <= periode_fin,
    ).count()
    budgets = _budgets_de_la_periode(db, id_client, periode_debut)
    nb_budgets_depasses = sum(1 for _, valeurs in budgets if valeurs["est_depasse"])
    return {
        "transactions_suspectes": nb_suspectes,
        "budgets_depasses": nb_budgets_depasses,
        "nombre_budgets_actifs": len(budgets),
    }


CALCULATEURS_ANALYSE = {
    "HABITUDES": calculer_habitudes,
    "TENDANCES": calculer_tendances,
    "COMPARAISON": calculer_comparaison,
    "COMPORTEMENT": calculer_comportement,
}


# --- Prédictions : DEPENSES_FUTURES, RISQUE_BUDGETAIRE, CAPACITE_EPARGNE ---

def predire_depenses_futures(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    # Toujours basé sur les derniers mois PLEINS avant aujourd'hui, jamais
    # avant periode_debut (qui est le mois futur prédit, pas une base
    # valable pour la moyenne).
    montant_predit = _moyenne_mensuelle(db, id_client, "DEPENSE", date.today().replace(day=1))
    recommandations = (
        f"Vos dépenses du mois prochain sont estimées à {montant_predit} XAF, "
        f"sur la base de votre moyenne des {NB_MOIS_MOYENNE_GLISSANTE} derniers mois."
    )
    # Heuristique fixe (pas un vrai intervalle de confiance statistique) :
    # une moyenne glissante simple a une fiabilité modérée, jamais parfaite.
    return {"montant_predit": montant_predit, "niveau_confiance": 0.6, "recommandations": recommandations}


def predire_risque_budgetaire(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    """Projette la dépense de fin de période au rythme actuel de chaque
    budget actif (jours écoulés vs jours totaux de la période)."""
    budgets = _budgets_de_la_periode(db, id_client, periode_debut)
    aujourdhui = date.today()
    jours_ecoules = max((min(aujourdhui, periode_fin) - periode_debut).days + 1, 1)
    jours_total = (periode_fin - periode_debut).days + 1

    a_risque = []
    montant_projete_total = Decimal("0")
    for budget, valeurs in budgets:
        if valeurs["est_depasse"]:
            continue
        projection = (valeurs["montant_depense"] / jours_ecoules * jours_total).quantize(Decimal("0.01"))
        if projection > budget.montant_limite:
            a_risque.append(f"{budget.categorie.nom} (projection {projection} XAF / limite {budget.montant_limite} XAF)")
            montant_projete_total += projection

    if a_risque:
        recommandations = "Au rythme actuel, ces budgets risquent d'être dépassés d'ici la fin du mois : " + ", ".join(a_risque) + "."
    else:
        recommandations = "Aucun budget ne semble à risque de dépassement au rythme actuel."

    return {
        "montant_predit": montant_projete_total if a_risque else None,
        "niveau_confiance": 0.5,
        "recommandations": recommandations,
    }


def predire_capacite_epargne(db: Session, id_client: int, periode_debut: date, periode_fin: date) -> dict:
    reference = date.today().replace(day=1)
    revenus_moyens = _moyenne_mensuelle(db, id_client, "REVENU", reference)
    depenses_moyennes = _moyenne_mensuelle(db, id_client, "DEPENSE", reference)
    capacite = revenus_moyens - depenses_moyennes

    if capacite <= 0:
        return {
            "montant_predit": Decimal("0"),
            "niveau_confiance": 0.5,
            "recommandations": "Vos dépenses moyennes couvrent ou dépassent vos revenus moyens : "
            "aucune capacité d'épargne prévisible ce mois-ci.",
        }

    return {
        "montant_predit": capacite,
        "niveau_confiance": 0.5,
        "recommandations": f"Vous pourriez épargner environ {capacite} XAF ce mois-ci, "
        f"sur la base de vos {NB_MOIS_MOYENNE_GLISSANTE} derniers mois.",
    }


CALCULATEURS_PREDICTION = {
    "DEPENSES_FUTURES": predire_depenses_futures,
    "RISQUE_BUDGETAIRE": predire_risque_budgetaire,
    "CAPACITE_EPARGNE": predire_capacite_epargne,
}


# --- Points d'entrée : courant (jamais persisté) et historique (snapshots) ---

def obtenir_analyse_courante(
    db: Session, id_client: int, type_: str, periode_debut: Optional[date] = None, periode_fin: Optional[date] = None
) -> dict:
    if type_ not in CALCULATEURS_ANALYSE:
        raise TypeAnalyseInvalideError()
    if periode_debut is None or periode_fin is None:
        periode_debut, periode_fin = _limites_mois(date.today().year, date.today().month)

    resultats = CALCULATEURS_ANALYSE[type_](db, id_client, periode_debut, periode_fin)
    score = calculer_score_financier(db, id_client, periode_debut, periode_fin)
    return {
        "type": type_,
        "periode_debut": periode_debut,
        "periode_fin": periode_fin,
        "resultats": resultats,
        "score_financier": score,
        "date_generation": datetime.utcnow(),
    }


def obtenir_prediction_courante(
    db: Session, id_client: int, type_: str, periode_debut: Optional[date] = None, periode_fin: Optional[date] = None
) -> dict:
    if type_ not in CALCULATEURS_PREDICTION:
        raise TypePredictionInvalideError()
    if periode_debut is None or periode_fin is None:
        if type_ == "RISQUE_BUDGETAIRE":
            # Le risque concerne les budgets du mois EN COURS, pas un mois futur.
            periode_debut, periode_fin = _limites_mois(date.today().year, date.today().month)
        else:
            periode_debut, periode_fin = _mois_suivant(date.today())

    donnees = CALCULATEURS_PREDICTION[type_](db, id_client, periode_debut, periode_fin)
    return {
        "type": type_,
        "periode_debut": periode_debut,
        "periode_fin": periode_fin,
        "date_generation": datetime.utcnow(),
        **donnees,
    }


def lister_historique_analyses(db: Session, id_client: int, type_: str) -> List[AnalyseFinanciere]:
    if type_ not in CALCULATEURS_ANALYSE:
        raise TypeAnalyseInvalideError()
    return (
        db.query(AnalyseFinanciere)
        .filter(AnalyseFinanciere.id_client == id_client, AnalyseFinanciere.type == type_)
        .order_by(AnalyseFinanciere.periode_debut.desc())
        .all()
    )


def lister_historique_predictions(db: Session, id_client: int, type_: str) -> List[Prediction]:
    if type_ not in CALCULATEURS_PREDICTION:
        raise TypePredictionInvalideError()
    return (
        db.query(Prediction)
        .filter(Prediction.id_client == id_client, Prediction.type == type_)
        .order_by(Prediction.periode_debut.desc())
        .all()
    )


def generer_snapshots_mensuels_tous_clients(db: Session) -> int:
    """
    Fige un snapshot AnalyseFinanciere + Prediction du mois précédent pour
    chaque client — appelé le 1er de chaque mois (voir worker.tasks). Sert
    uniquement à construire un historique dans le temps : /analyse et
    /analyse/predictions (courant) recalculent toujours en direct et
    n'écrivent jamais dans ces tables.
    """
    aujourdhui = date.today()
    mois_precedent = aujourdhui.month - 1 or 12
    annee_precedente = aujourdhui.year if aujourdhui.month > 1 else aujourdhui.year - 1
    periode_debut, periode_fin = _limites_mois(annee_precedente, mois_precedent)

    nb_generes = 0
    for (id_client,) in db.query(Client.id_client).all():
        for type_ in CALCULATEURS_ANALYSE:
            donnees = obtenir_analyse_courante(db, id_client, type_, periode_debut, periode_fin)
            db.add(AnalyseFinanciere(id_client=id_client, **donnees))
            nb_generes += 1
        for type_ in CALCULATEURS_PREDICTION:
            donnees = obtenir_prediction_courante(db, id_client, type_, periode_debut, periode_fin)
            db.add(Prediction(id_client=id_client, **donnees))
            nb_generes += 1

    db.commit()
    return nb_generes
