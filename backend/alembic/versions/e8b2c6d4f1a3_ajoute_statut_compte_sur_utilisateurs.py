"""ajoute_statut_compte_sur_utilisateurs

Revision ID: e8b2c6d4f1a3
Revises: d7a3b5c1e9f2
Create Date: 2026-09-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b2c6d4f1a3'
down_revision: Union[str, Sequence[str], None] = 'd7a3b5c1e9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Distingue la suspension (temporaire) de la désactivation (compte fermé).
    Les comptes déjà bloqués (est_actif = false) sont repris comme SUSPENDU.
    """
    op.add_column(
        'utilisateurs',
        sa.Column('statut_compte', sa.String(length=20), server_default='ACTIF', nullable=False),
    )
    op.execute("UPDATE utilisateurs SET statut_compte = 'SUSPENDU' WHERE est_actif = false")


def downgrade() -> None:
    op.drop_column('utilisateurs', 'statut_compte')
