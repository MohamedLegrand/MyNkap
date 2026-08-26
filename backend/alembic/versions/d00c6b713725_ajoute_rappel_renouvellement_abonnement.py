"""ajoute rappel renouvellement abonnement

Revision ID: d00c6b713725
Revises: 3a13f682b6fe
Create Date: 2026-08-26 09:24:58.047876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd00c6b713725'
down_revision: Union[str, Sequence[str], None] = '3a13f682b6fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('abonnements', sa.Column('rappel_renouvellement_envoye', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('abonnements', 'rappel_renouvellement_envoye')
