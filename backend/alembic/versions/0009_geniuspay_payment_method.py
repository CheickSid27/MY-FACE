"""payment_method.geniuspay : nouvelle valeur enum pour la passerelle GeniusPay
(chemin de paiement isole, en test sandbox — voir routers/geniuspay.py)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE ne peut pas etre annule dans la meme
    # transaction (limitation Postgres) : autocommit isole cette commande.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'geniuspay'")


def downgrade() -> None:
    # Postgres ne supporte pas la suppression d'une valeur d'enum : aucune
    # action possible sans recreer le type (non fait ici, risque de perte de
    # donnees si des commandes utilisent deja cette valeur).
    pass
