"""orders.printed_at : date d'impression des tirages papier d'une commande

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("printed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "printed_at")
