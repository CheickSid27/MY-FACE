"""Verification de l'e-mail, sessions revoquees au changement de mot de
passe, conservation des donnees

- users : date de confirmation de l'adresse e-mail, date du dernier
  changement de mot de passe ;
- events : exemption de la suppression automatique (evenement de
  demonstration), date de suppression des photos.

Les comptes deja en base ont ete crees avant la verification de l'e-mail :
ils sont consideres comme confirmes (date de creation du compte).

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET email_verified_at = created_at")

    op.add_column(
        "events", sa.Column("retention_exempt", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column("events", sa.Column("photos_purged_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "photos_purged_at")
    op.drop_column("events", "retention_exempt")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "email_verified_at")
