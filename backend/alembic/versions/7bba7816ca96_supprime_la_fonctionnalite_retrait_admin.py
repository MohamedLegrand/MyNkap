"""supprime la fonctionnalite retrait admin

Revision ID: 7bba7816ca96
Revises: a95e360154f1
Create Date: 2026-08-25 10:15:09.420205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7bba7816ca96'
down_revision: Union[str, Sequence[str], None] = 'a95e360154f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Le retrait (Cash-Out) admin est supprimé — la table était vide
    # (aucun retrait réel n'avait jamais été effectué), aucune perte
    # d'historique financier.
    op.drop_index(op.f('ix_retraits_id_retrait'), table_name='retraits')
    op.drop_index(op.f('ix_retraits_reference_hrpay'), table_name='retraits')
    op.drop_table('retraits')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('retraits',
    sa.Column('id_retrait', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('id_administrateur', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('montant', sa.NUMERIC(precision=14, scale=2), autoincrement=False, nullable=False),
    sa.Column('devise', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('pays', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('phone_number', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('operator', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('reference_hrpay', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('statut', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('date_creation', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('date_confirmation', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['id_administrateur'], ['administrateurs.id_administrateur'], name=op.f('retraits_id_administrateur_fkey')),
    sa.PrimaryKeyConstraint('id_retrait', name=op.f('retraits_pkey'))
    )
    op.create_index(op.f('ix_retraits_reference_hrpay'), 'retraits', ['reference_hrpay'], unique=True)
    op.create_index(op.f('ix_retraits_id_retrait'), 'retraits', ['id_retrait'], unique=False)
    # ### end Alembic commands ###
