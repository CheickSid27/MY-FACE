"""events.short_code : code court de l'evenement (adresse /e/CODE)

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-22

"""
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Copie de services/short_codes.py (une migration ne doit pas dependre du code
# de l'application, qui peut changer ensuite).
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LENGTH = 8


def upgrade() -> None:
    op.add_column("events", sa.Column("short_code", sa.String(10), nullable=True))
    # Un code pour chaque evenement deja cree : les anciens liens et QR codes
    # (/event/<identifiant>) continuent de marcher.
    conn = op.get_bind()
    used: set[str] = set()
    for (event_id,) in conn.execute(sa.text("SELECT id FROM events")).all():
        code = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
        while code in used:
            code = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
        used.add(code)
        conn.execute(sa.text("UPDATE events SET short_code = :code WHERE id = :id"), {"code": code, "id": event_id})
    op.create_index("ix_events_short_code", "events", ["short_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_events_short_code", table_name="events")
    op.drop_column("events", "short_code")
