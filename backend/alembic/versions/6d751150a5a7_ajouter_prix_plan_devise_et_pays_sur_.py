"""ajouter prix_plan_devise et pays sur paiements_abonnement

Revision ID: 6d751150a5a7
Revises: eeaddd66920f
Create Date: 2026-08-19 11:30:45.856141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d751150a5a7'
down_revision: Union[str, Sequence[str], None] = 'eeaddd66920f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Prix (mensuel, annuel) par devise pour les plans payants. XAF/XOF ont la
# même valeur réelle que les prix XAF déjà en place (peg euro commun) : pas
# de conversion. CDF/GNF/GMD sont des ESTIMATIONS approximatives (calculées
# à partir de taux de change généraux, pas d'un flux temps réel) — à faire
# valider côté business avant mise en production.
PRIX_PAR_DEVISE = {
    "ESSENTIEL": {
        "XAF": (1000, 10000),
        "XOF": (1000, 10000),
        "CDF": (4700, 47000),   # estimé
        "GNF": (14400, 144000),  # estimé
        "GMD": (120, 1200),      # estimé
    },
    "PREMIUM": {
        "XAF": (2500, 25000),
        "XOF": (2500, 25000),
        "CDF": (11800, 118000),  # estimé
        "GNF": (36000, 360000),  # estimé
        "GMD": (290, 2900),      # estimé
    },
}


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'prix_plan_devise',
        sa.Column('id_prix', sa.Integer(), nullable=False),
        sa.Column('id_plan', sa.Integer(), nullable=False),
        sa.Column('devise', sa.String(), nullable=False),
        sa.Column('prix_mensuel', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('prix_annuel', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['id_plan'], ['plans.id_plan']),
        sa.PrimaryKeyConstraint('id_prix'),
        sa.UniqueConstraint('id_plan', 'devise', name='uq_prix_plan_devise'),
    )
    op.create_index(op.f('ix_prix_plan_devise_id_prix'), 'prix_plan_devise', ['id_prix'], unique=False)

    op.add_column(
        'paiements_abonnement',
        sa.Column('pays', sa.String(), nullable=False, server_default='CM'),
    )

    # Seed : résout id_plan par nom (pas d'ID codé en dur, robuste à l'ordre
    # de création des plans).
    conn = op.get_bind()
    table = sa.table(
        'prix_plan_devise',
        sa.column('id_plan', sa.Integer()),
        sa.column('devise', sa.String()),
        sa.column('prix_mensuel', sa.Numeric(14, 2)),
        sa.column('prix_annuel', sa.Numeric(14, 2)),
    )
    for nom_plan, prix_devises in PRIX_PAR_DEVISE.items():
        id_plan = conn.execute(
            sa.text("SELECT id_plan FROM plans WHERE nom = :nom"), {"nom": nom_plan}
        ).scalar()
        if id_plan is None:
            continue  # plan absent de cette base (ex. tests) : rien à seeder
        rows = [
            {"id_plan": id_plan, "devise": devise, "prix_mensuel": mensuel, "prix_annuel": annuel}
            for devise, (mensuel, annuel) in prix_devises.items()
        ]
        op.bulk_insert(table, rows)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('paiements_abonnement', 'pays')
    op.drop_index(op.f('ix_prix_plan_devise_id_prix'), table_name='prix_plan_devise')
    op.drop_table('prix_plan_devise')
