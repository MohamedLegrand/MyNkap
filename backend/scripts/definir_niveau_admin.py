"""
Change le niveau d'acces d'un administrateur deja existant.

Complementaire de creer_premier_admin.py : celui-la cree le tout premier
admin (probleme de l'oeuf et de la poule), celui-ci sert a promouvoir ou
retrograder un admin deja en base sans passer par l'API (utile quand aucun
Superadmin n'existe encore pour appeler PATCH /admin/admins/{id}/level).

Usage :
    python scripts/definir_niveau_admin.py <email> <niveau_acces>

Exemple :
    python scripts/definir_niveau_admin.py mohamed.legrand@perenkap.online 3
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import models_registry  # noqa: F401 (enregistre toutes les tables/relations)
from app.core.database import SessionLocal
from app.modules.auth.models import Administrateur


def definir_niveau_admin(email: str, niveau_acces: int) -> None:
    db = SessionLocal()
    try:
        admin = db.query(Administrateur).filter(Administrateur.email == email).first()
        if admin is None:
            print(f"Aucun administrateur avec l'email '{email}' — rien a faire.")
            return

        ancien_niveau = admin.niveau_acces
        admin.niveau_acces = niveau_acces
        db.commit()
        print(f"Administrateur '{admin.username}' ({email}) : niveau_acces {ancien_niveau} -> {niveau_acces}.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage : python scripts/definir_niveau_admin.py <email> <niveau_acces>")
        sys.exit(1)

    definir_niveau_admin(sys.argv[1], int(sys.argv[2]))
