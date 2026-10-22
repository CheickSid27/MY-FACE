"""photos.raw_key : fichier RAW garde tel quel a cote du JPEG pleine resolution

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("raw_key", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("photos", "raw_key")
