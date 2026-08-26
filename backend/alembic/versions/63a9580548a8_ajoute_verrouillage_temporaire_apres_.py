"""ajoute verrouillage temporaire apres echecs de connexion repetes

Revision ID: 63a9580548a8
Revises: d00c6b713725
Create Date: 2026-08-26 09:51:14.393995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63a9580548a8'
down_revision: Union[str, Sequence[str], None] = 'd00c6b713725'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('utilisateurs', sa.Column('verrouille_jusqua', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('utilisateurs', 'verrouille_jusqua')
