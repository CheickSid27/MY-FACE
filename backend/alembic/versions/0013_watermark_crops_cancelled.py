"""Apercu filigrane (telephone invite), cle de vignette-visage memorisee,
statut de commande 'cancelled'

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Meme contrainte que 0009/0010 : ALTER TYPE ... ADD VALUE doit etre
    # isole de la transaction de migration.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'cancelled'")

    op.add_column("photos", sa.Column("preview_watermarked_key", sa.String(512), nullable=True))
    op.add_column("face_embeddings", sa.Column("crop_key", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("face_embeddings", "crop_key")
    op.drop_column("photos", "preview_watermarked_key")
    # Retrait de la valeur enum 'cancelled' non supporte par Postgres sans
    # recreer le type (meme choix que 0009/0010).
