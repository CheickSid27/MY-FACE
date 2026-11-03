"""event_sections : parties d'un evenement (mairie, reception...) ; photos.section_id

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_event_sections_event_id", "event_sections", ["event_id"])
    # Les photos deja en ligne restent sans partie : l'evenement s'affiche comme avant.
    op.add_column(
        "photos",
        sa.Column("section_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("event_sections.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_photos_section_id", "photos", ["section_id"])


def downgrade() -> None:
    op.drop_index("ix_photos_section_id", table_name="photos")
    op.drop_column("photos", "section_id")
    op.drop_index("ix_event_sections_event_id", table_name="event_sections")
    op.drop_table("event_sections")
