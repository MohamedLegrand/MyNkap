"""ajouter prochaine_invitation_avis sur clients

Revision ID: adc9fb729c9b
Revises: f4b0524afbc9
Create Date: 2026-08-20 14:29:08.310053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adc9fb729c9b'
down_revision: Union[str, Sequence[str], None] = 'f4b0524afbc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('clients', sa.Column('prochaine_invitation_avis', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('clients', 'prochaine_invitation_avis')
