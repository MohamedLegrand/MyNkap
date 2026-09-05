"""corrige_les_descriptions_dette_creance_avec_id_brut

Revision ID: b73d4a162d6e
Revises: 364218653763
Create Date: 2026-09-05 14:41:34.153793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b73d4a162d6e'
down_revision: Union[str, Sequence[str], None] = '364218653763'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Corrige les transactions REMBOURSEMENT_DETTE/ENCAISSEMENT_CREANCE déjà
    en base dont la description exposait l'ID technique brut ("Remboursement
    de la dette #14", et même "Encaissement de la dette #16" pour une
    créance — bug qui écrivait toujours "dette" quel que soit le type) au
    lieu du nom donné par le client (voir dettes.service._operer, corrigé
    pour écrire désormais "{verbe} : {dette.nom}"). Migration de données
    pure : aucun changement de schéma.
    """
    op.execute(
        """
        UPDATE transactions AS t
        SET description = CASE
            WHEN t.type = 'REMBOURSEMENT_DETTE' THEN 'Remboursement : ' || d.nom
            WHEN t.type = 'ENCAISSEMENT_CREANCE' THEN 'Encaissement : ' || d.nom
        END
        FROM dettes AS d
        WHERE t.id_dette = d.id_dette
          AND t.type IN ('REMBOURSEMENT_DETTE', 'ENCAISSEMENT_CREANCE')
          AND t.description LIKE '% de la dette #%'
        """
    )


def downgrade() -> None:
    """Pas de retour en arrière possible : l'ID d'origine remplacé par le
    nom n'est plus reconstituable tel quel (même principe que la migration
    364218653763)."""
    pass
