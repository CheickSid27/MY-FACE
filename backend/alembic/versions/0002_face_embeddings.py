"""pgvector extension + face_embeddings table with HNSW index

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 512


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "face_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "photo_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("photos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vector", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("bounding_box", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_face_embeddings_photo_id", "face_embeddings", ["photo_id"])

    # Index HNSW pour la recherche approximative de plus proche voisin (distance cosinus).
    # Parametres de depart recommandes par le cahier des charges (section 3.3),
    # a ajuster apres tests de charge en Phase 5.
    op.execute(
        "CREATE INDEX ix_face_embeddings_vector_hnsw ON face_embeddings "
        "USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_face_embeddings_vector_hnsw")
    op.drop_index("ix_face_embeddings_photo_id", table_name="face_embeddings")
    op.drop_table("face_embeddings")
