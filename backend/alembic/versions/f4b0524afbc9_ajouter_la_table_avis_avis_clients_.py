"""ajouter la table avis (avis clients moderes)

Revision ID: f4b0524afbc9
Revises: df8122ccfcae
Create Date: 2026-08-20 12:13:59.253995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b0524afbc9'
down_revision: Union[str, Sequence[str], None] = 'df8122ccfcae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'avis',
        sa.Column('id_avis', sa.Integer(), nullable=False),
        sa.Column('id_client', sa.Integer(), nullable=False),
        sa.Column('note', sa.Integer(), nullable=False),
        sa.Column('commentaire', sa.Text(), nullable=False),
        sa.Column('statut', sa.String(), nullable=False),
        sa.Column('date_creation', sa.DateTime(), nullable=True),
        sa.Column('date_moderation', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_client'], ['clients.id_client']),
        sa.PrimaryKeyConstraint('id_avis'),
        sa.UniqueConstraint('id_client', name='uq_avis_id_client'),
    )
    op.create_index(op.f('ix_avis_id_avis'), 'avis', ['id_avis'], unique=False)
    op.create_index(op.f('ix_avis_id_client'), 'avis', ['id_client'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_avis_id_client'), table_name='avis')
    op.drop_index(op.f('ix_avis_id_avis'), table_name='avis')
    op.drop_table('avis')
