"""marque_verifies_les_comptes_existants

Revision ID: f3a7c9d2b5e1
Revises: e8b2c6d4f1a3
Create Date: 2026-09-25 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3a7c9d2b5e1'
down_revision: Union[str, Sequence[str], None] = 'e8b2c6d4f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    La connexion exige désormais l'e-mail vérifié (voir
    auth.services.authentifier_utilisateur, EmailNonVerifieError) —
    jusqu'ici purement déclaratif, rien ne l'imposait réellement. Tous les
    comptes créés avant ce correctif ont pu se connecter sans jamais
    vérifier leur e-mail ; les bloquer rétroactivement, sans avertissement,
    romprait l'accès de clients par ailleurs légitimes. On les considère
    donc vérifiés une bonne fois pour toutes ; seules les inscriptions à
    partir de maintenant devront réellement passer par le code reçu par
    e-mail.
    """
    op.execute("UPDATE utilisateurs SET email_verifie = true WHERE email_verifie = false")


def downgrade() -> None:
    # Irréversible par nature (on ne sait plus qui était vraiment vérifié
    # avant ce correctif) — pas de downgrade utile ici.
    pass
