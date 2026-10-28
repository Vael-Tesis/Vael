"""Tabla candidato_tags con su política de RLS (DEV-C-05, DEC-010)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-25

Asigna etiquetas a candidatos. La tabla nace con la RLS habilitada y forzada y con la
política `aislamiento_tenant`, en la misma migración que la crea (CLAUDE.md, reglas
multiempresa).
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidato_tags",
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("candidato_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tag_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["candidato_id"], ["candidatos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("candidato_id", "tag_id"),
    )
    op.create_index(op.f("ix_candidato_tags_tenant_id"), "candidato_tags", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_candidato_tags_tag_id"), "candidato_tags", ["tag_id"], unique=False)

    op.execute("ALTER TABLE candidato_tags ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE candidato_tags FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY aislamiento_tenant ON candidato_tags "
        "USING (tenant_id = current_setting('app.tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
    )


def downgrade() -> None:
    op.drop_table("candidato_tags")
