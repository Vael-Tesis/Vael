"""Sesiones con refresh token rotativo y token_version del usuario (DEV-A-02, DEC-011)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-10-25

La tabla `sesiones` nace con su política de RLS en la misma migración (DEC-010).
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("usuarios", "token_version", server_default=None)

    op.create_table(
        "sesiones",
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("usuario_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("token_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
        sa.Column("revocado_en", sa.DateTime(), nullable=True),
        sa.Column("reemplazado_por", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["reemplazado_por"], ["sesiones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sesiones_tenant_id"), "sesiones", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_sesiones_usuario_id"), "sesiones", ["usuario_id"], unique=False)

    op.execute("ALTER TABLE sesiones ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sesiones FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY aislamiento_tenant ON sesiones "
        "USING (tenant_id = current_setting('app.tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
    )


def downgrade() -> None:
    op.drop_table("sesiones")
    op.drop_column("usuarios", "token_version")
