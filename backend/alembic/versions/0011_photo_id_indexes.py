"""Index sur cart_items.photo_id et order_items.photo_id

Ces FK n'etaient pas indexees individuellement (cart_items avait seulement
l'index compose issu de uq_cart_item_photo, dont photo_id n'est pas la
colonne de tete) : filtrer par photo_id seul (ajout au panier, suppression
d'une photo) finissait en full scan de la table a mesure qu'elle grossit.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-09

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_cart_items_photo_id", "cart_items", ["photo_id"])
    op.create_index("ix_order_items_photo_id", "order_items", ["photo_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_photo_id", table_name="order_items")
    op.drop_index("ix_cart_items_photo_id", table_name="cart_items")
