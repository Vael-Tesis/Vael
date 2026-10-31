"""Banco de talento: Candidato.en_banco_talento (DEV-A-08, HU-14)

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-11-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidatos", sa.Column("en_banco_talento", sa.Boolean(), nullable=False, server_default="false"))
    op.alter_column("candidatos", "en_banco_talento", server_default=None)


def downgrade() -> None:
    op.drop_column("candidatos", "en_banco_talento")
