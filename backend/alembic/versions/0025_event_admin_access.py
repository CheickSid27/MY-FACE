"""events.admin_access : le photographe autorise l'equipe MYFACE a gerer son evenement

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("admin_access", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("events", sa.Column("admin_access_since", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "admin_access_since")
    op.drop_column("events", "admin_access")
