"""met a jour les prix essentiel et premium

Revision ID: 466dfd24d0ce
Revises: 63a9580548a8
Create Date: 2026-08-27 18:54:03.364790

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '466dfd24d0ce'
down_revision: Union[str, Sequence[str], None] = '63a9580548a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pure migration de données (aucun changement de schéma) : nouveaux tarifs
# ESSENTIEL (1000 -> 2500 XAF/mois) et PREMIUM (2500 -> 5000 XAF/mois).
# Les devises CDF/GNF/GMD (estimations approximatives, voir la migration
# 6d751150a5a7_ajouter_prix_plan_devise...) sont mises à l'échelle par le
# même facteur que le prix XAF de référence (x2,5 pour ESSENTIEL, x2 pour
# PREMIUM) pour préserver le taux de change implicite déjà en place.

def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE plans SET prix_mensuel = 2500, prix_annuel = 25000 WHERE nom = 'ESSENTIEL'")
    op.execute("UPDATE plans SET prix_mensuel = 5000, prix_annuel = 50000 WHERE nom = 'PREMIUM'")

    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 2500, prix_annuel = 25000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise IN ('XAF', 'XOF')
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 11750, prix_annuel = 117500
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise = 'CDF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 36000, prix_annuel = 360000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise = 'GNF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 300, prix_annuel = 3000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise = 'GMD'
    """)

    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 5000, prix_annuel = 50000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise IN ('XAF', 'XOF')
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 23600, prix_annuel = 236000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise = 'CDF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 72000, prix_annuel = 720000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise = 'GNF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 580, prix_annuel = 5800
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise = 'GMD'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE plans SET prix_mensuel = 1000, prix_annuel = 10000 WHERE nom = 'ESSENTIEL'")
    op.execute("UPDATE plans SET prix_mensuel = 2500, prix_annuel = 25000 WHERE nom = 'PREMIUM'")

    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 1000, prix_annuel = 10000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise IN ('XAF', 'XOF')
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 4700, prix_annuel = 47000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise = 'CDF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 14400, prix_annuel = 144000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise = 'GNF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 120, prix_annuel = 1200
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'ESSENTIEL') AND devise = 'GMD'
    """)

    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 2500, prix_annuel = 25000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise IN ('XAF', 'XOF')
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 11800, prix_annuel = 118000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise = 'CDF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 36000, prix_annuel = 360000
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise = 'GNF'
    """)
    op.execute("""
        UPDATE prix_plan_devise SET prix_mensuel = 290, prix_annuel = 2900
        WHERE id_plan = (SELECT id_plan FROM plans WHERE nom = 'PREMIUM') AND devise = 'GMD'
    """)
