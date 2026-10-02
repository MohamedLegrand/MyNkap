"""ajoute_inscriptions_en_attente

Revision ID: a1b2c3d4e5f6
Revises: 6125341fff9a
Create Date: 2026-10-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6125341fff9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Nouveau flux d'inscription : le Client n'est plus créé à POST
    /auth/register puis vérifié après coup, mais seulement une fois le
    code OTP confirmé (voir auth.models.PendingInscription et
    auth.services.confirmer_inscription) — un abandon avant l'OTP ne laisse
    plus de compte permanent en base. Les comptes créés avant cette
    migration, encore non vérifiés, continuent d'être gérés par l'ancien
    mécanisme (Utilisateur.otp_code) ; cette table ne concerne que les
    inscriptions démarrées après.
    """
    op.create_table(
        'inscriptions_en_attente',
        sa.Column('id_inscription', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('mot_de_passe', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('otp_code', sa.String(length=6), nullable=True),
        sa.Column('otp_expiration', sa.DateTime(), nullable=True),
        sa.Column('date_creation', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id_inscription'),
    )
    op.create_index(op.f('ix_inscriptions_en_attente_id_inscription'), 'inscriptions_en_attente', ['id_inscription'], unique=False)
    op.create_index(op.f('ix_inscriptions_en_attente_email'), 'inscriptions_en_attente', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_inscriptions_en_attente_email'), table_name='inscriptions_en_attente')
    op.drop_index(op.f('ix_inscriptions_en_attente_id_inscription'), table_name='inscriptions_en_attente')
    op.drop_table('inscriptions_en_attente')
