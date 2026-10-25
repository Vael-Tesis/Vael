"""Supervisión humana: estados por confirmar, decisiones_candidato y contacto de la empresa (DEV-C-10)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-25

- DEC-009: estados `cv_por_confirmar` y `examen_por_confirmar`, y la tabla de solo
  inserción `decisiones_candidato`, con su RLS en la misma migración (DEC-010).
- DEC-013: `empresas.email_contacto`, el contacto para consultas sobre datos personales
  que lleva el correo de cierre.
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ESTADOS_ANTERIORES = (
    "POSTULADO",
    "CV_ANALIZANDO",
    "CV_APROBADO",
    "CV_RECHAZADO",
    "EXAMEN_PENDIENTE",
    "EXAMEN_RENDIDO",
    "EXAMEN_APROBADO",
    "EXAMEN_RECHAZADO",
    "ENTREVISTA_PENDIENTE",
    "ENTREVISTA_REALIZADA",
    "FINALISTA",
    "CONTRATADO",
    "DESCARTADO",
)


def upgrade() -> None:
    op.execute("ALTER TYPE estadocandidato ADD VALUE IF NOT EXISTS 'CV_POR_CONFIRMAR' AFTER 'CV_ANALIZANDO'")
    op.execute("ALTER TYPE estadocandidato ADD VALUE IF NOT EXISTS 'EXAMEN_POR_CONFIRMAR' AFTER 'EXAMEN_RENDIDO'")

    op.add_column("empresas", sa.Column("email_contacto", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))

    op.create_table(
        "decisiones_candidato",
        sa.Column("tenant_id", sqlmodel.sql.sqltypes.AutoString(length=36), nullable=False),
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("candidato_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("etapa", sa.Enum("CV", "EXAMEN", "ENTREVISTA", name="etapadecision"), nullable=False),
        sa.Column("recomendacion_ia", sa.Enum("AVANZAR", "DESCARTAR", name="tipodecision"), nullable=True),
        sa.Column("puntaje", sa.Float(), nullable=True),
        sa.Column("umbral", sa.Float(), nullable=True),
        sa.Column("justificacion_ia", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "decision",
            sa.Enum("AVANZAR", "DESCARTAR", name="tipodecision", create_type=False),
            nullable=False,
        ),
        sa.Column("coincide_con_ia", sa.Boolean(), nullable=True),
        sa.Column("justificacion_humana", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("decidido_por", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("revision_inicio", sa.DateTime(), nullable=True),
        sa.Column("decidido_en", sa.DateTime(), nullable=False),
        sa.Column("reemplaza_a", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["candidato_id"], ["candidatos.id"]),
        sa.ForeignKeyConstraint(["decidido_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["reemplaza_a"], ["decisiones_candidato.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decisiones_candidato_tenant_id"), "decisiones_candidato", ["tenant_id"], unique=False)
    op.create_index(
        op.f("ix_decisiones_candidato_candidato_id"), "decisiones_candidato", ["candidato_id"], unique=False
    )

    op.execute("ALTER TABLE decisiones_candidato ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE decisiones_candidato FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY aislamiento_tenant ON decisiones_candidato "
        "USING (tenant_id = current_setting('app.tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
    )


def downgrade() -> None:
    op.drop_table("decisiones_candidato")
    op.execute("DROP TYPE tipodecision")
    op.execute("DROP TYPE etapadecision")
    op.drop_column("empresas", "email_contacto")

    # PostgreSQL no permite quitar valores de un enum: se recrea el tipo sin los dos estados,
    # devolviendo antes a los candidatos por confirmar al estado automático previo.
    op.execute("UPDATE candidatos SET estado = 'CV_ANALIZANDO' WHERE estado = 'CV_POR_CONFIRMAR'")
    op.execute("UPDATE candidatos SET estado = 'EXAMEN_RENDIDO' WHERE estado = 'EXAMEN_POR_CONFIRMAR'")
    op.execute("ALTER TYPE estadocandidato RENAME TO estadocandidato_dec009")
    valores = ", ".join(f"'{valor}'" for valor in _ESTADOS_ANTERIORES)
    op.execute(f"CREATE TYPE estadocandidato AS ENUM ({valores})")
    op.execute(
        "ALTER TABLE candidatos ALTER COLUMN estado TYPE estadocandidato USING estado::text::estadocandidato"
    )
    op.execute("DROP TYPE estadocandidato_dec009")
