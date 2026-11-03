"""Candidato.score_desglose: desglose ponderado de score_cv (DEC-024, DEV-C-14)

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-11-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("candidatos", sa.Column("score_desglose", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("candidatos", "score_desglose")
