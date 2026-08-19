"""ajouter la table retraits (Cash-Out HR-Skills Pay)

Revision ID: df8122ccfcae
Revises: 6d751150a5a7
Create Date: 2026-08-19 18:49:08.524858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df8122ccfcae'
down_revision: Union[str, Sequence[str], None] = '6d751150a5a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'retraits',
        sa.Column('id_retrait', sa.Integer(), nullable=False),
        sa.Column('id_administrateur', sa.Integer(), nullable=False),
        sa.Column('montant', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('devise', sa.String(), nullable=False),
        sa.Column('pays', sa.String(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('operator', sa.String(), nullable=False),
        sa.Column('reference_hrpay', sa.String(), nullable=False),
        sa.Column('statut', sa.String(), nullable=False),
        sa.Column('date_creation', sa.DateTime(), nullable=True),
        sa.Column('date_confirmation', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['id_administrateur'], ['administrateurs.id_administrateur']),
        sa.PrimaryKeyConstraint('id_retrait'),
    )
    op.create_index(op.f('ix_retraits_id_retrait'), 'retraits', ['id_retrait'], unique=False)
    op.create_index(op.f('ix_retraits_reference_hrpay'), 'retraits', ['reference_hrpay'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_retraits_reference_hrpay'), table_name='retraits')
    op.drop_index(op.f('ix_retraits_id_retrait'), table_name='retraits')
    op.drop_table('retraits')
