"""payment_method.paystack : paiement en ligne des photos par Paystack
(evenements de MYFACE, voir routers/payments.py)

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE hors transaction (limitation Postgres).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'paystack'")


def downgrade() -> None:
    # Postgres ne sait pas retirer une valeur d'enum (voir 0009).
    pass
