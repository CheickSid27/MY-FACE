"""event_payment_methods table, orders.status awaiting_confirmation

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'awaiting_confirmation'")

    # Le type "payment_method" existe deja (migration 0004) : create_type=False
    # pour ne pas tenter de le recreer.
    payment_method_enum = postgresql.ENUM(
        "wave", "orange_money", "mtn_money", "moov_money", "manual",
        name="payment_method",
        create_type=False,
    )

    op.create_table(
        "event_payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", payment_method_enum, nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("qr_image_key", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "method", name="uq_event_payment_method"),
    )
    op.create_index("ix_event_payment_methods_event_id", "event_payment_methods", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_payment_methods_event_id", table_name="event_payment_methods")
    op.drop_table("event_payment_methods")
    # Postgres ne permet pas de retirer une valeur d'un type ENUM existant
    # sans le recreer entierement ; on laisse 'awaiting_confirmation' en
    # place au downgrade (valeur inutilisee mais inoffensive).
