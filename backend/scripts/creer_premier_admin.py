"""
Bootstrap du tout premier administrateur de la plateforme.

POST /admin/admins exige deja un administrateur authentifie avec
niveau_acces >= 2 pour en creer un nouveau — sans point d'entree separe,
il n'existe donc aucun moyen de creer le tout premier administrateur via
l'API elle-meme (probleme de l'oeuf et de la poule). Ce script est ce
point d'entree, a executer manuellement une seule fois par environnement
(local, puis a nouveau lors du premier deploiement en production).

Usage :
    python scripts/creer_premier_admin.py <email> <username> <mot_de_passe> [niveau_acces]

Exemple :
    python scripts/creer_premier_admin.py admin@mynkap.com admin 123456789 3
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import models_registry  # noqa: F401 (enregistre toutes les tables/relations)
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.modules.auth.models import Administrateur, Utilisateur


def creer_premier_admin(email: str, username: str, mot_de_passe: str, niveau_acces: int = 3) -> None:
    db = SessionLocal()
    try:
        if db.query(Utilisateur).filter(Utilisateur.email == email).first():
            print(f"Un utilisateur avec l'email '{email}' existe deja — rien a faire.")
            return

        admin = Administrateur(
            email=email,
            username=username,
            mot_de_passe=get_password_hash(mot_de_passe),
            niveau_acces=niveau_acces,
            est_actif=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Administrateur '{username}' cree avec succes (id={admin.id_administrateur}, niveau_acces={niveau_acces}).")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage : python scripts/creer_premier_admin.py <email> <username> <mot_de_passe> [niveau_acces]")
        sys.exit(1)

    email_arg = sys.argv[1]
    username_arg = sys.argv[2]
    mot_de_passe_arg = sys.argv[3]
    niveau_acces_arg = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    creer_premier_admin(email_arg, username_arg, mot_de_passe_arg, niveau_acces_arg)
