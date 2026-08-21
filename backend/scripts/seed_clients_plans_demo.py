"""
Cree trois clients de demonstration, un par palier tarifaire :
- un client abonne ESSENTIEL (paiement simule confirme)
- un client abonne PREMIUM (paiement simule confirme)
- un client sur le forfait GRATUIT (aucun paiement)

Chacun recoit des comptes financiers et un historique de transactions
realiste, pour tester le comportement de l'application (limites d'acces
par palier, analyse, JARVIS) sur les trois profils.

Passe par les fonctions de service reelles (auth.services.creer_client,
plans.service.changer_plan, comptes.service, transactions.service) —
jamais d'INSERT SQL brut. Le paiement Mobile Money reel (HR-Skills Pay)
n'est jamais appele ici : un enregistrement PaiementAbonnement SUCCESS est
insere directement pour simuler une confirmation deja recue, comme le
ferait verifier_paiements_en_attente() en conditions reelles.

Usage :
    python scripts/seed_clients_plans_demo.py
"""
import sys
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import models_registry  # noqa: F401
from app.core.database import SessionLocal
from app.modules.auth.models import Client
from app.modules.auth.schemas import UserRegister
from app.modules.auth import services as auth_services
from app.modules.plans import service as plans_service
from app.modules.plans.models import Plan, PaiementAbonnement
from app.modules.comptes import service as comptes_service
from app.modules.comptes.schemas import CompteFinancierCreate
from app.modules.budgets import service as budgets_service
from app.modules.transactions import service as transactions_service
from app.modules.transactions.schemas import TransactionCreate
from app.modules.transactions.service import SoldeInsuffisantError

random.seed(7)

DATE_DEBUT = date(2025, 9, 1)
DATE_FIN = date(2026, 8, 21)

PROFILS = [
    {
        "email": "essentiel.demo@mynkap.dev",
        "first_name": "Aicha",
        "last_name": "Moussa",
        "phone": "+237600000001",
        "plan": "ESSENTIEL",
        "nb_transactions": 250,
    },
    {
        "email": "premium.demo@mynkap.dev",
        "first_name": "Junior",
        "last_name": "Mbala",
        "phone": "+237600000002",
        "plan": "PREMIUM",
        "nb_transactions": 250,
    },
    {
        "email": "gratuit.demo@mynkap.dev",
        "first_name": "Fatou",
        "last_name": "Diallo",
        "phone": "+237600000003",
        "plan": "GRATUIT",
        "nb_transactions": 250,
    },
]

MOT_DE_PASSE_DEMO = "DemoMyNkap2026!"

FOURCHETTES_DEPENSE = {
    "Alimentation": (1000, 15000),
    "Transport": (500, 8000),
    "Logement": (20000, 150000),
    "Santé": (2000, 30000),
    "Éducation": (5000, 50000),
    "Factures & Services": (3000, 40000),
    "Loisirs": (1000, 20000),
    "Achats personnels": (1000, 25000),
    "Autres dépenses": (500, 10000),
}
FOURCHETTES_REVENU = {
    "Salaire": (150000, 350000),
    "Business": (10000, 200000),
    "Transferts reçus": (5000, 100000),
    "Autres revenus": (1000, 50000),
}
DEFAUT_FOURCHETTE = (1000, 20000)


def date_aleatoire():
    delta_jours = (DATE_FIN - DATE_DEBUT).days
    return DATE_DEBUT + timedelta(days=random.randint(0, delta_jours))


def obtenir_ou_creer_client(db, profil) -> Client:
    existant = db.query(Client).filter(Client.email == profil["email"]).first()
    if existant is not None:
        print(f"Client deja existant : {profil['email']} (id_client={existant.id_client})")
        return existant

    client = auth_services.creer_client(
        db,
        UserRegister(
            email=profil["email"],
            mot_de_passe=MOT_DE_PASSE_DEMO,
            first_name=profil["first_name"],
            last_name=profil["last_name"],
            phone=profil["phone"],
        ),
    )
    print(f"Client cree : {profil['email']} (id_client={client.id_client})")
    return client


def activer_plan(db, client: Client, nom_plan: str) -> None:
    if nom_plan == "GRATUIT":
        plans_service.changer_plan(db, client.id_client, "GRATUIT")
        print(f"  Plan GRATUIT active pour {client.email}.")
        return

    plan = db.query(Plan).filter(Plan.nom == nom_plan).first()
    reference = f"seed-demo-{client.id_client}-{nom_plan.lower()}"
    deja_paye = db.query(PaiementAbonnement).filter(PaiementAbonnement.reference_hrpay == reference).first()
    if deja_paye is None:
        paiement = PaiementAbonnement(
            id_client=client.id_client,
            id_plan_demande=plan.id_plan,
            cycle_facturation="MENSUEL",
            montant=plan.prix_mensuel,
            devise=plan.devise,
            pays="CM",
            reference_hrpay=reference,
            statut="SUCCESS",
            date_confirmation=datetime.utcnow(),
        )
        db.add(paiement)
        db.commit()
        print(f"  Paiement simule SUCCESS enregistre ({plan.prix_mensuel} {plan.devise}).")

    plans_service.changer_plan(db, client.id_client, nom_plan, "MENSUEL")
    print(f"  Plan {nom_plan} active pour {client.email}.")


def creer_comptes(db, client: Client) -> list:
    existants = comptes_service.lister_comptes(db, client.id_client)
    if existants:
        return existants

    comptes = [
        comptes_service.creer_compte(
            db, client.id_client,
            CompteFinancierCreate(nom="Mobile Money", type="MOBILE_MONEY", devise="XAF", solde_initial=Decimal("50000")),
        ),
        comptes_service.creer_compte(
            db, client.id_client,
            CompteFinancierCreate(nom="Compte bancaire", type="BANCAIRE", devise="XAF", solde_initial=Decimal("20000")),
        ),
    ]
    print(f"  Comptes crees : {[(c.nom, c.type) for c in comptes]}")
    return comptes


def generer_transactions(db, client: Client, comptes: list, nb_evenements: int) -> None:
    categories = budgets_service.obtenir_categories(db, client.id_client)
    cats_depense = [c for c in categories if c.type == "DEPENSE" and c.est_actif]
    cats_revenu = [c for c in categories if c.type == "REVENU" and c.est_actif]
    if not cats_depense or not cats_revenu:
        print("  Pas de categories disponibles, transactions ignorees.")
        return

    sim_solde = {c.id_compte: c.solde for c in comptes}
    evenements = []

    cat_salaire = next((c for c in cats_revenu if c.nom == "Salaire"), cats_revenu[0])
    compte_principal = comptes[0]
    mois_courant = date(DATE_DEBUT.year, DATE_DEBUT.month, 28)
    while mois_courant <= DATE_FIN:
        evenements.append({
            "date": mois_courant, "id_compte": compte_principal.id_compte,
            "id_categorie": cat_salaire.id_categorie, "type": "REVENU",
            "montant": Decimal(random.randint(180000, 320000)), "description": "Salaire mensuel",
        })
        annee = mois_courant.year + (1 if mois_courant.month == 12 else 0)
        mois = 1 if mois_courant.month == 12 else mois_courant.month + 1
        mois_courant = date(annee, mois, 28)

    for _ in range(nb_evenements):
        compte = random.choice(comptes)
        est_depense = random.random() < 0.72
        if est_depense:
            cat = random.choice(cats_depense)
            mini, maxi = FOURCHETTES_DEPENSE.get(cat.nom, DEFAUT_FOURCHETTE)
        else:
            cat = random.choice(cats_revenu)
            mini, maxi = FOURCHETTES_REVENU.get(cat.nom, DEFAUT_FOURCHETTE)
        montant = Decimal(random.randint(mini, maxi))
        evenements.append({
            "date": date_aleatoire(), "id_compte": compte.id_compte,
            "id_categorie": cat.id_categorie, "type": "DEPENSE" if est_depense else "REVENU",
            "montant": montant, "description": None,
        })

    evenements.sort(key=lambda e: e["date"])

    nb_creees = 0
    nb_ignorees = 0
    for evt in evenements:
        solde_actuel = sim_solde[evt["id_compte"]]
        montant = evt["montant"]
        if evt["type"] == "DEPENSE":
            if solde_actuel < Decimal("200"):
                nb_ignorees += 1
                continue
            if montant > solde_actuel:
                montant = (solde_actuel * Decimal("0.6")).quantize(Decimal("1"))
                if montant < Decimal("100"):
                    nb_ignorees += 1
                    continue
        try:
            transactions_service.enregistrer_transaction(
                db, client.id_client,
                TransactionCreate(
                    id_compte=evt["id_compte"], id_categorie=evt["id_categorie"],
                    montant=montant, type=evt["type"], description=evt["description"], date=evt["date"],
                ),
            )
            if evt["type"] == "DEPENSE":
                sim_solde[evt["id_compte"]] -= montant
            else:
                sim_solde[evt["id_compte"]] += montant
            nb_creees += 1
        except SoldeInsuffisantError:
            nb_ignorees += 1
        except Exception as exc:
            print(f"    Erreur ignoree : {exc}")
            db.rollback()
            nb_ignorees += 1

    print(f"  Transactions creees : {nb_creees} (ignorees : {nb_ignorees})")


def main():
    db = SessionLocal()
    try:
        for profil in PROFILS:
            print(f"--- {profil['plan']} : {profil['email']} ---")
            client = obtenir_ou_creer_client(db, profil)
            activer_plan(db, client, profil["plan"])
            comptes = creer_comptes(db, client)
            generer_transactions(db, client, comptes, profil["nb_transactions"])
        print("Termine.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
