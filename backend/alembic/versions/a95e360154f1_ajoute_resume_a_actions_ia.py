"""ajoute resume a actions_ia

Revision ID: a95e360154f1
Revises: adc9fb729c9b
Create Date: 2026-08-22 17:51:15.168730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a95e360154f1'
down_revision: Union[str, Sequence[str], None] = 'adc9fb729c9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ActionIA n'a jamais été instanciée en base avant cette migration
    # (voir jarvis/service.py, module encore non branché) : la table est
    # garantie vide, une colonne NOT NULL sans défaut est donc sûre ici.
    op.add_column('actions_ia', sa.Column('resume', sa.String(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('actions_ia', 'resume')
