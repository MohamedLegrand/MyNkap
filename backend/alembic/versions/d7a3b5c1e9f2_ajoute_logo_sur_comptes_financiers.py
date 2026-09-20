"""ajoute_logo_sur_comptes_financiers

Revision ID: d7a3b5c1e9f2
Revises: c4f1a9e7d2b8
Create Date: 2026-09-20 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a3b5c1e9f2'
down_revision: Union[str, Sequence[str], None] = 'c4f1a9e7d2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Logo personnalisable par compte : chemin d'un logo prédéfini du frontend
    ou URL d'un logo importé (hébergé par MyNkap). NULL = aucun choix
    (comptes existants inchangés : le frontend retombe sur le logo par
    défaut du type, ou laisse le logo vide).
    """
    op.add_column("comptes_financiers", sa.Column("logo", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("comptes_financiers", "logo")
