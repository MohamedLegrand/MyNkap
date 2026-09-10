"""ajoute_paiement_par_carte_bancaire

Revision ID: c4f1a9e7d2b8
Revises: b73d4a162d6e
Create Date: 2026-09-10 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f1a9e7d2b8'
down_revision: Union[str, Sequence[str], None] = 'b73d4a162d6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Ouvre le paiement par carte bancaire (E-NKAP via HR-Skills Pay) à côté
    du Mobile Money existant, pour les deux points d'entrée : recharge de
    compte (recharges_compte) et souscription d'abonnement
    (paiements_abonnement).

    Trois colonnes par table :
    - methode : MOBILE_MONEY (défaut, rétro-compatible avec les lignes
      existantes) ou CARTE.
    - montant_facture : montant réellement débité sur la carte, commission
      incluse (le compte/l'abonnement est crédité de `montant`, le client
      règle `montant_facture`). NULL pour le Mobile Money.
    - checkout_url : page de paiement hébergée Flocash (carte seulement).

    La référence carte ("card_xxxx") réutilise la colonne unique
    `reference_hrpay` : c'est bien une référence HR-Skills Pay, et l'unicité
    reste pertinente.
    """
    for table in ("recharges_compte", "paiements_abonnement"):
        op.add_column(
            table,
            sa.Column(
                "methode",
                sa.String(),
                nullable=False,
                server_default="MOBILE_MONEY",
            ),
        )
        op.add_column(table, sa.Column("montant_facture", sa.Numeric(14, 2), nullable=True))
        op.add_column(table, sa.Column("checkout_url", sa.String(), nullable=True))


def downgrade() -> None:
    for table in ("recharges_compte", "paiements_abonnement"):
        op.drop_column(table, "checkout_url")
        op.drop_column(table, "montant_facture")
        op.drop_column(table, "methode")
