"""Photos offertes par l'organisateur : moyen de paiement « offert »

Le mode lui-meme est un drapeau dans Event.pricing (JSON, pas de colonne) ;
seule la valeur d'enum est nouvelle, pour reconnaitre ces commandes.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'offert'")


def downgrade() -> None:
    # Une valeur d'enum Postgres ne se retire pas simplement ; rien a faire.
    pass
