"""Paiement en especes (borne uniquement) + tirage papier par photo dans le panier

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'cash'")

    op.add_column(
        "events", sa.Column("cash_enabled", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "cart_items", sa.Column("print_requested", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "order_items", sa.Column("print_requested", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("order_items", sa.Column("print_price", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("order_items", "print_price")
    op.drop_column("order_items", "print_requested")
    op.drop_column("cart_items", "print_requested")
    op.drop_column("events", "cash_enabled")
    # Retrait de la valeur enum 'cash' non supporte par Postgres sans recreer
    # le type (non fait ici, voir 0009 pour le meme choix sur 'geniuspay').
