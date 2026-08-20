"""drop photos.original_url / thumbnail_url (bucket now private, URLs signed on read)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("photos", "original_url")
    op.drop_column("photos", "thumbnail_url")


def downgrade() -> None:
    op.add_column("photos", sa.Column("thumbnail_url", sa.String(1024), nullable=False, server_default=""))
    op.add_column("photos", sa.Column("original_url", sa.String(1024), nullable=False, server_default=""))
