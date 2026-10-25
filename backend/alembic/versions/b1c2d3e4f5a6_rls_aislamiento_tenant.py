"""RLS de aislamiento por tenant en todas las tablas con tenant_id (DEC-010)

Revision ID: b1c2d3e4f5a6
Revises: 48978732de6a
Create Date: 2026-10-25

Cada tabla con datos de una empresa queda con RLS habilitada y forzada (también para su
dueño) y con la política única `aislamiento_tenant`. Si `app.tenant_id` no está fijado,
current_setting(..., true) devuelve NULL y ninguna fila es visible ni modificable.

Las tablas que se creen en adelante incluyen su política en la misma migración que las
crea (CLAUDE.md, reglas multiempresa); tests/test_rls.py falla si alguna queda sin ella.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "48978732de6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLAS_CON_TENANT = (
    "empresas",
    "usuarios",
    "tokens_acceso",
    "areas",
    "plantillas_evaluacion",
    "dimensiones_evaluacion",
    "vacantes",
    "candidatos",
    "tags",
    "notas_candidato",
    "examenes",
    "preguntas_examen",
    "eventos_auditoria",
    "entrevistas_ia",
    "capturas_auditoria",
)


def upgrade() -> None:
    for tabla in TABLAS_CON_TENANT:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY aislamiento_tenant ON {tabla} "
            "USING (tenant_id = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
        )


def downgrade() -> None:
    for tabla in TABLAS_CON_TENANT:
        op.execute(f"DROP POLICY IF EXISTS aislamiento_tenant ON {tabla}")
        op.execute(f"ALTER TABLE {tabla} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY")
