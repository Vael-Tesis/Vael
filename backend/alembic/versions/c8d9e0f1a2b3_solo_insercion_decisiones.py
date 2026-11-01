"""Solo inserción en decisiones_candidato: revoca UPDATE/DELETE a vael_app y vael_system (DEC-009, RF-A-12)

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-11-01

DEC-009 exige que `decisiones_candidato` sea de solo inserción; hasta ahora solo lo
garantizaba una convención de código (ningún módulo la edita ni la borra), verificada por
una prueba estática. Esta migración lo refuerza en la base de datos: ni `vael_app` (la
aplicación) ni `vael_system` (la lista cerrada) conservan UPDATE ni DELETE sobre esta tabla,
solo SELECT e INSERT.

`app/scripts/crear_roles.py` repite esta misma revocación cada vez que se ejecuta: su
`GRANT ... ON ALL TABLES` corre antes que las migraciones en todo arranque observado
(`scripts/aws-encender.ps1`, `.github/workflows/ci.yml`, `tests/conftest.py`) y volvería a
otorgar UPDATE/DELETE si no se repitiera ahí. Esta migración cierra el hueco de un primer
arranque desde cero, donde la tabla no existe todavía cuando `crear_roles.py` corre.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE UPDATE, DELETE ON decisiones_candidato FROM vael_app, vael_system")


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE ON decisiones_candidato TO vael_app, vael_system")
