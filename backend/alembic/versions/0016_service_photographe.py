"""Service photographe : profils, packs par evenement, achats de packs

- users : profil du photographe (nom, studio, telephone, ville), compte actif
  ou suspendu, date d'acceptation des conditions ;
- events : pack achete, limite de photos negociee, texte du filigrane, mot de
  passe de galerie (hash) ;
- pack_purchases : achats de packs (declares par le photographe, valides par
  un admin) ;
- app_settings : reglages globaux (numeros Mobile Money de MYFACE).

Les evenements deja en base existaient avant le service photographe : ils
passent en « sur_mesure » (aucune limite), seuls les nouveaux evenements
commencent au pack Decouverte.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("studio_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "events", sa.Column("pack", sa.String(length=20), server_default="decouverte", nullable=False)
    )
    op.add_column("events", sa.Column("photo_limit_override", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("watermark_text", sa.String(length=40), nullable=True))
    op.add_column("events", sa.Column("gallery_password_hash", sa.String(length=255), nullable=True))
    op.execute("UPDATE events SET pack = 'sur_mesure'")

    op.create_table(
        "pack_purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pack", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="XOF", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("payer_phone", sa.String(length=32), nullable=True),
        sa.Column("transaction_ref", sa.String(length=80), nullable=True),
        sa.Column("admin_note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "decided_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_pack_purchases_event_id", "pack_purchases", ["event_id"])
    op.create_index("ix_pack_purchases_user_id", "pack_purchases", ["user_id"])
    op.create_index("ix_pack_purchases_status", "pack_purchases", ["status"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_pack_purchases_status", table_name="pack_purchases")
    op.drop_index("ix_pack_purchases_user_id", table_name="pack_purchases")
    op.drop_index("ix_pack_purchases_event_id", table_name="pack_purchases")
    op.drop_table("pack_purchases")
    op.drop_column("events", "gallery_password_hash")
    op.drop_column("events", "watermark_text")
    op.drop_column("events", "photo_limit_override")
    op.drop_column("events", "pack")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "city")
    op.drop_column("users", "phone")
    op.drop_column("users", "studio_name")
    op.drop_column("users", "display_name")
