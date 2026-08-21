"""
Genere un gros volume de donnees realistes pour le client "mohamedlegrand"
(legrandmohamed67@gmail.com, id_client=50) : comptes, categories,
transactions (le plus possible), transactions recurrentes, templates et
tontines supplementaires. But : stress-tester l'analyse/les previsions de
l'application sur un historique volumineux.

Passe exclusivement par les fonctions de service reelles (comptes.service,
transactions.service, budgets.service, tontines.service) pour respecter
les invariants (solde >= 0, montant > 0, resynchro ComptePrincipal,
detection de transaction suspecte) — jamais d'INSERT SQL brut.

Usage :
    python scripts/seed_donnees_demo_mohamedlegrand.py
"""
import sys
import os
import random
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import models_registry  # noqa: F401
from app.core.database import SessionLocal
from app.modules.auth.models import Client
from app.modules.comptes import service as comptes_service
from app.modules.comptes.schemas import CompteFinancierCreate
from app.modules.budgets import service as budgets_service
from app.modules.budgets.schemas import CategorieCreate
from app.modules.budgets.service import CategorieDejaExistanteError
from app.modules.transactions import service as transactions_service
from app.modules.transactions.schemas import TransactionCreate, TransactionRecurrenteCreate, TemplateTransactionCreate
from app.modules.transactions.service import SoldeInsuffisantError
from app.modules.tontines import service as tontines_service
from app.modules.tontines.schemas import TontineCreate, MembreTontineCreate

EMAIL_CIBLE = "legrandmohamed67@gmail.com"
random.seed(42)

NOUVELLES_CATEGORIES = [
    {"nom": "Assurance", "type": "DEPENSE"},
    {"nom": "Impots & Taxes", "type": "DEPENSE"},
    {"nom": "Cadeaux & Dons", "type": "DEPENSE"},
    {"nom": "Abonnements", "type": "DEPENSE"},
    {"nom": "Investissements", "type": "REVENU"},
    {"nom": "Ventes", "type": "REVENU"},
]

# Nom de categorie -> (montant_min, montant_max)
FOURCHETTES_DEPENSE = {
    "Alimentation": (1000, 15000),
    "alimentation": (1000, 15000),
    "Transport": (500, 8000),
    "Logement": (20000, 150000),
    "Sante": (2000, 30000),
    "Santé": (2000, 30000),
    "Education": (5000, 50000),
    "Éducation": (5000, 50000),
    "Factures & Services": (3000, 40000),
    "Loisirs": (1000, 20000),
    "Achats personnels": (1000, 25000),
    "Autres depenses": (500, 10000),
    "Autres dépenses": (500, 10000),
    "voyage": (10000, 120000),
    "Assurance": (5000, 25000),
    "Impots & Taxes": (10000, 100000),
    "Cadeaux & Dons": (1000, 20000),
    "Abonnements": (1000, 15000),
}
FOURCHETTES_REVENU = {
    "Business": (10000, 200000),
    "Transferts reçus": (5000, 100000),
    "Transferts recus": (5000, 100000),
    "Autres revenus": (1000, 50000),
    "rapport": (1000, 50000),
    "Investissements": (5000, 100000),
    "Ventes": (2000, 80000),
}
DEFAUT_FOURCHETTE = (1000, 20000)

NB_EVENEMENTS = 1200
DATE_DEBUT = date(2024, 8, 1)
DATE_FIN = date(2026, 8, 20)


def get_or_create_categorie(db, id_client, nom, type_):
    try:
        cat = budgets_service.creer_categorie(db, id_client, CategorieCreate(nom=nom, type=type_))
        db.commit()
        return cat
    except CategorieDejaExistanteError:
        db.rollback()
        from app.modules.budgets.models import Categorie
        return db.query(Categorie).filter(
            Categorie.id_client == id_client, Categorie.nom == nom, Categorie.type == type_
        ).first()


def date_aleatoire():
    delta_jours = (DATE_FIN - DATE_DEBUT).days
    return DATE_DEBUT + timedelta(days=random.randint(0, delta_jours))


def main():
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.email == EMAIL_CIBLE).first()
        if client is None:
            print(f"Aucun client avec l'email '{EMAIL_CIBLE}' — abandon.")
            return
        id_client = client.id_client
        print(f"Client cible : id_client={id_client} ({client.first_name} {client.last_name})")

        comptes = comptes_service.lister_comptes(db, id_client)
        noms_comptes = {c.nom for c in comptes}

        if "Compte bancaire" not in noms_comptes:
            nouveau = comptes_service.creer_compte(
                db, id_client, CompteFinancierCreate(nom="Compte bancaire", type="BANCAIRE", devise="XAF", solde_initial=Decimal("0"))
            )
            comptes.append(nouveau)
            print(f"Compte cree : {nouveau.nom} (id={nouveau.id_compte})")

        if "Espèces courante" not in noms_comptes:
            nouveau = comptes_service.creer_compte(
                db, id_client, CompteFinancierCreate(nom="Espèces courante", type="ESPECES", devise="XAF", solde_initial=Decimal("5000"))
            )
            comptes.append(nouveau)
            print(f"Compte cree : {nouveau.nom} (id={nouveau.id_compte})")

        comptes = comptes_service.lister_comptes(db, id_client)
        print(f"Comptes actifs : {[(c.id_compte, c.nom, c.type) for c in comptes]}")

        for cat_def in NOUVELLES_CATEGORIES:
            get_or_create_categorie(db, id_client, cat_def["nom"], cat_def["type"])
        categories = budgets_service.obtenir_categories(db, id_client)

        cats_depense = [c for c in categories if c.type == "DEPENSE" and c.est_actif]
        cats_revenu = [c for c in categories if c.type == "REVENU" and c.est_actif]
        print(f"Categories DEPENSE ({len(cats_depense)}) : {[c.nom for c in cats_depense]}")
        print(f"Categories REVENU ({len(cats_revenu)}) : {[c.nom for c in cats_revenu]}")

        cat_salaire = next((c for c in cats_revenu if c.nom == "Salaire"), cats_revenu[0])
        compte_salaire = next((c for c in comptes if c.nom == "MOMO"), comptes[0])

        sim_solde = {c.id_compte: c.solde for c in comptes}

        evenements = []

        mois_courant = date(DATE_DEBUT.year, DATE_DEBUT.month, 28)
        while mois_courant <= DATE_FIN:
            evenements.append({
                "date": mois_courant,
                "id_compte": compte_salaire.id_compte,
                "id_categorie": cat_salaire.id_categorie,
                "type": "REVENU",
                "montant": Decimal(random.randint(180000, 320000)),
                "description": "Salaire mensuel",
            })
            annee = mois_courant.year + (1 if mois_courant.month == 12 else 0)
            mois = 1 if mois_courant.month == 12 else mois_courant.month + 1
            mois_courant = date(annee, mois, 28)

        comptes_ponderes = comptes + [c for c in comptes if c.type in ("MOBILE_MONEY", "BANCAIRE")]

        for _ in range(NB_EVENEMENTS):
            compte = random.choice(comptes_ponderes)
            est_depense = random.random() < 0.72
            if est_depense:
                cat = random.choice(cats_depense)
                mini, maxi = FOURCHETTES_DEPENSE.get(cat.nom, DEFAUT_FOURCHETTE)
            else:
                cat = random.choice(cats_revenu)
                mini, maxi = FOURCHETTES_REVENU.get(cat.nom, DEFAUT_FOURCHETTE)
            montant = Decimal(random.randint(mini, maxi))
            evenements.append({
                "date": date_aleatoire(),
                "id_compte": compte.id_compte,
                "id_categorie": cat.id_categorie,
                "type": "DEPENSE" if est_depense else "REVENU",
                "montant": montant,
                "description": None,
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
                    db,
                    id_client,
                    TransactionCreate(
                        id_compte=evt["id_compte"],
                        id_categorie=evt["id_categorie"],
                        montant=montant,
                        type=evt["type"],
                        description=evt["description"],
                        date=evt["date"],
                    ),
                )
                if evt["type"] == "DEPENSE":
                    sim_solde[evt["id_compte"]] -= montant
                else:
                    sim_solde[evt["id_compte"]] += montant
                nb_creees += 1
                if nb_creees % 100 == 0:
                    print(f"  ... {nb_creees} transactions creees")
            except SoldeInsuffisantError:
                nb_ignorees += 1
            except Exception as exc:
                print(f"  Erreur ignoree sur un evenement : {exc}")
                db.rollback()
                nb_ignorees += 1

        print(f"Transactions creees : {nb_creees} (ignorees : {nb_ignorees})")

        prochain_mois = date(DATE_FIN.year, DATE_FIN.month, 28) + timedelta(days=31)
        prochain_mois = prochain_mois.replace(day=1)

        compte_bancaire = next((c for c in comptes if c.type == "BANCAIRE"), comptes[0])
        cat_logement = next((c for c in cats_depense if c.nom == "Logement"), cats_depense[0])
        cat_abonnements = next((c for c in cats_depense if c.nom == "Abonnements"), cats_depense[0])
        cat_autres_revenus = next((c for c in cats_revenu if "Autres" in c.nom), cats_revenu[0])
        compte_epargne = next((c for c in comptes if c.type == "EPARGNE"), comptes[0])

        recurrences = [
            TransactionRecurrenteCreate(
                id_compte=compte_bancaire.id_compte, id_categorie=cat_logement.id_categorie,
                montant=Decimal("60000"), type="DEPENSE", description="Loyer mensuel",
                frequence="MENSUELLE", prochaine_execution=prochain_mois,
            ),
            TransactionRecurrenteCreate(
                id_compte=compte_salaire.id_compte, id_categorie=cat_abonnements.id_categorie,
                montant=Decimal("5000"), type="DEPENSE", description="Abonnement streaming",
                frequence="MENSUELLE", prochaine_execution=prochain_mois,
            ),
            TransactionRecurrenteCreate(
                id_compte=compte_epargne.id_compte, id_categorie=cat_autres_revenus.id_categorie,
                montant=Decimal("10000"), type="REVENU", description="Epargne automatique",
                frequence="MENSUELLE", prochaine_execution=prochain_mois,
            ),
        ]
        nb_recurrentes = 0
        for r in recurrences:
            try:
                transactions_service.creer_transaction_recurrente(db, id_client, r)
                nb_recurrentes += 1
            except Exception as exc:
                print(f"  Recurrence ignoree : {exc}")
                db.rollback()
        print(f"Transactions recurrentes creees : {nb_recurrentes}")

        cat_alimentation = next((c for c in cats_depense if "limentation" in c.nom), cats_depense[0])
        cat_transport = next((c for c in cats_depense if c.nom == "Transport"), cats_depense[0])
        cat_business = next((c for c in cats_revenu if c.nom == "Business"), cats_revenu[0])
        compte_orange = next((c for c in comptes if c.nom == "orange"), comptes[0])

        templates = [
            TemplateTransactionCreate(
                id_compte=compte_salaire.id_compte, id_categorie=cat_alimentation.id_categorie,
                nom="Courses hebdo", montant=Decimal("8000"), type="DEPENSE", description="Courses de la semaine",
            ),
            TemplateTransactionCreate(
                id_compte=compte_orange.id_compte, id_categorie=cat_transport.id_categorie,
                nom="Taxi", montant=Decimal("1500"), type="DEPENSE", description="Trajet taxi",
            ),
            TemplateTransactionCreate(
                id_compte=compte_salaire.id_compte, id_categorie=cat_business.id_categorie,
                nom="Freelance", montant=Decimal("50000"), type="REVENU", description="Mission freelance",
            ),
        ]
        nb_templates = 0
        for t in templates:
            try:
                transactions_service.creer_template(db, id_client, t)
                nb_templates += 1
            except Exception as exc:
                print(f"  Template ignore : {exc}")
                db.rollback()
        print(f"Templates crees : {nb_templates}")

        tontines_existantes = {t.nom for t in tontines_service.lister_tontines(db, id_client)}
        nouvelles_tontines = [
            TontineCreate(
                nom="Tontine du travail", montant_cotisation=Decimal("25000"), devise="XAF",
                frequence="MENSUELLE", date_debut=date(2025, 1, 5),
                membres=[
                    MembreTontineCreate(nom="Aicha"), MembreTontineCreate(nom="Bruno"),
                    MembreTontineCreate(nom="Chantal"), MembreTontineCreate(nom="David"),
                    MembreTontineCreate(nom="Estelle"), MembreTontineCreate(nom="mohamedlegrand"),
                ],
            ),
            TontineCreate(
                nom="Tontine famille", montant_cotisation=Decimal("5000"), devise="XAF",
                frequence="HEBDOMADAIRE", date_debut=date(2026, 3, 2),
                membres=[
                    MembreTontineCreate(nom="Papa"), MembreTontineCreate(nom="Maman"),
                    MembreTontineCreate(nom="Grand frere"), MembreTontineCreate(nom="mohamedlegrand"),
                ],
            ),
        ]
        nb_tontines = 0
        for t in nouvelles_tontines:
            if t.nom in tontines_existantes:
                continue
            try:
                tontines_service.creer_tontine(db, id_client, t)
                nb_tontines += 1
            except Exception as exc:
                print(f"  Tontine ignoree : {exc}")
                db.rollback()
        print(f"Tontines creees : {nb_tontines}")

        print("Termine.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
