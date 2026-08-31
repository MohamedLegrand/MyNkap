"""reduit a 7 jours les essais existants encore sur 30 jours

Revision ID: 364218653763
Revises: 466dfd24d0ce
Create Date: 2026-08-31 09:12:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '364218653763'
down_revision: Union[str, Sequence[str], None] = '466dfd24d0ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pure migration de données (aucun changement de schéma). La durée de
# l'essai gratuit est passée de 30 à 7 jours dans le code (voir
# plans.service.DUREE_ESSAI_GRATUIT), mais ce changement ne s'applique
# qu'aux nouvelles inscriptions — les abonnements ESSAI déjà créés avant
# ce changement gardaient leur date_fin calculée sur l'ancienne règle des
# 30 jours. Recale ici tous les essais encore en cours sur la nouvelle
# règle (date_debut + 7 jours) : si cette date est déjà passée, le client
# repassera simplement en GRATUIT au prochain accès (voir
# plans.service.obtenir_abonnement_actif, comportement déjà existant).

def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        UPDATE abonnements
        SET date_fin = date_debut + INTERVAL '7 days'
        WHERE statut = 'ESSAI'
          AND date_fin IS NOT NULL
          AND date_fin > date_debut + INTERVAL '7 days'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Correction de données ponctuelle : l'ancienne date_fin exacte n'est
    # pas conservée, aucun downgrade fiable n'est possible.
    pass
