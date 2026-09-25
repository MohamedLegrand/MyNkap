"""ajoute_date_revocation_sur_refresh_tokens

Revision ID: 6125341fff9a
Revises: f3a7c9d2b5e1
Create Date: 2026-09-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6125341fff9a'
down_revision: Union[str, Sequence[str], None] = 'f3a7c9d2b5e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Horodatage de révocation d'un refresh token — jusqu'ici seul le booléen
    est_revoque existait, sans savoir QUAND la révocation a eu lieu. Sert à
    la détection de réutilisation (voir auth.services.valider_refresh_token,
    FENETRE_GRACE_REUTILISATION) : une fenêtre de grâce de quelques secondes
    évite de traiter comme un vol de session une simple retentative réseau
    du client juste après une rotation (réponse perdue en transit), tout en
    continuant à traiter une réapparition plus tardive comme suspecte.
    """
    op.add_column('refresh_tokens', sa.Column('date_revocation', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('refresh_tokens', 'date_revocation')
