"""users : compte de versement Paystack du photographe (partage des paiements)

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("paystack_subaccount_code", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("payout_method", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("payout_account", sa.String(40), nullable=True))
    op.add_column("users", sa.Column("payout_name", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("payout_enabled", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    for column in ("payout_enabled", "payout_name", "payout_account", "payout_method", "paystack_subaccount_code"):
        op.drop_column("users", column)
