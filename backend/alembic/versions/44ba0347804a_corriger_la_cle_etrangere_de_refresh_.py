"""corriger la cle etrangere de refresh_tokens vers utilisateurs (corrige le crash de connexion admin)

Revision ID: 44ba0347804a
Revises: ecac5edb6613
Create Date: 2026-07-27 09:53:40.211172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44ba0347804a'
down_revision: Union[str, Sequence[str], None] = 'ecac5edb6613'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('refresh_tokens_id_client_fkey'), 'refresh_tokens', type_='foreignkey')
    op.create_foreign_key(
        'fk_refresh_tokens_id_client_utilisateurs', 'refresh_tokens', 'utilisateurs', ['id_client'], ['id_utilisateur']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_refresh_tokens_id_client_utilisateurs', 'refresh_tokens', type_='foreignkey')
    op.create_foreign_key(op.f('refresh_tokens_id_client_fkey'), 'refresh_tokens', 'clients', ['id_client'], ['id_client'])
