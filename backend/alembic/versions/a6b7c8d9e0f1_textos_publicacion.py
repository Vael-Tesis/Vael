"""Textos de publicación de la vacante (DEV-A-04, HU-10)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-10-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vacantes", sa.Column("textos_publicacion", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("vacantes", "textos_publicacion")
