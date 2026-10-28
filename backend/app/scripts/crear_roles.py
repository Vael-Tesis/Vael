"""Crea o actualiza los tres roles de base de datos de DEC-010 y sus privilegios.

Uso (con DATABASE_ADMIN_URL apuntando a un usuario administrador del servidor):

    python -m app.scripts.crear_roles

Lee el usuario y la contraseña de cada rol de DATABASE_URL (vael_app),
DATABASE_SYSTEM_URL (vael_system) y DATABASE_OWNER_URL (vael_owner), y la base de
destino de DATABASE_OWNER_URL. Es idempotente: se puede ejecutar en cada despliegue.

La aplicación nunca se conecta como administrador: DATABASE_ADMIN_URL solo lo usa este
script, y en producción no se define en el contenedor de la app.
"""
import asyncio
import sys
from dataclasses import dataclass

import asyncpg
from sqlalchemy.engine import URL, make_url

from app.core.config import settings

ROL_APP = "vael_app"
ROL_SYSTEM = "vael_system"
ROL_OWNER = "vael_owner"

# vael_app y vael_owner quedan sujetos a la RLS; solo vael_system la omite (lista cerrada).
_ATRIBUTOS = {
    ROL_OWNER: "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS",
    ROL_APP: "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS",
    ROL_SYSTEM: "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS",
}


@dataclass(frozen=True)
class Credencial:
    usuario: str
    password: str


def _credencial(url_texto: str, rol_esperado: str, variable: str) -> Credencial:
    url = make_url(url_texto)
    if url.username != rol_esperado:
        raise ValueError(f"{variable} debe conectarse como {rol_esperado}, no como {url.username!r}")
    if not url.password:
        raise ValueError(f"{variable} no tiene contraseña")
    return Credencial(url.username, url.password)


def url_admin() -> URL:
    """URL del administrador del servidor (DATABASE_ADMIN_URL)."""
    valor = settings.database_admin_url
    if not valor:
        raise SystemExit("Falta DATABASE_ADMIN_URL (usuario administrador del servidor PostgreSQL)")
    return make_url(valor)


async def crear_roles(
    admin: URL,
    base_destino: str,
    *,
    app: Credencial,
    system: Credencial,
    owner: Credencial,
) -> None:
    """Crea o actualiza los roles y deja a vael_owner como dueño de todo el esquema public."""
    conexion = await asyncpg.connect(
        user=admin.username,
        password=admin.password,
        host=admin.host,
        port=admin.port or 5432,
        database=base_destino,
    )
    try:
        # En RDS el administrador no es superusuario (rds_superuser)
        es_superusuario = await conexion.fetchval("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        for credencial in (owner, app, system):
            existe = await conexion.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", credencial.usuario)
            verbo = "ALTER" if existe else "CREATE"
            atributos = _ATRIBUTOS[credencial.usuario]
            if existe and not es_superusuario:
                # Solo un superusuario puede nombrar el atributo SUPERUSER en un ALTER ROLE; un rol
                # creado por quien no es superusuario nunca lo tiene, así que la garantía se mantiene
                atributos = atributos.replace("NOSUPERUSER ", "")
            sentencia = await conexion.fetchval(
                f"SELECT format('{verbo} ROLE %I WITH {atributos} PASSWORD %L', $1::text, $2::text)",
                credencial.usuario,
                credencial.password,
            )
            await conexion.execute(sentencia)

        # Sin ser superusuario, para pasar objetos a vael_owner y fijar sus privilegios por
        # defecto el administrador debe ser miembro de vael_owner. En local no hace falta.
        if not es_superusuario:
            await conexion.execute(f"GRANT {ROL_OWNER} TO CURRENT_USER")

        await conexion.execute(
            f'GRANT CONNECT ON DATABASE "{base_destino}" TO {ROL_OWNER}, {ROL_APP}, {ROL_SYSTEM}'
        )
        await conexion.execute(f"GRANT USAGE, CREATE ON SCHEMA public TO {ROL_OWNER}")
        await conexion.execute(f"GRANT USAGE ON SCHEMA public TO {ROL_APP}, {ROL_SYSTEM}")

        # Objetos creados antes de existir vael_owner (p. ej. por un superusuario en desarrollo):
        # pasan a vael_owner para que las migraciones puedan alterarlos y la RLS se aplique.
        await conexion.execute(f"""
            DO $$
            DECLARE objeto record;
            BEGIN
              FOR objeto IN SELECT tablename FROM pg_tables
                            WHERE schemaname = 'public' AND tableowner <> '{ROL_OWNER}' LOOP
                EXECUTE format('ALTER TABLE public.%I OWNER TO {ROL_OWNER}', objeto.tablename);
              END LOOP;
              FOR objeto IN SELECT c.relname FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = 'public' AND c.relkind = 'S'
                              AND pg_get_userbyid(c.relowner) <> '{ROL_OWNER}' LOOP
                EXECUTE format('ALTER SEQUENCE public.%I OWNER TO {ROL_OWNER}', objeto.relname);
              END LOOP;
              FOR objeto IN SELECT t.typname FROM pg_type t
                            JOIN pg_namespace n ON n.oid = t.typnamespace
                            WHERE n.nspname = 'public' AND t.typtype = 'e'
                              AND pg_get_userbyid(t.typowner) <> '{ROL_OWNER}' LOOP
                EXECUTE format('ALTER TYPE public.%I OWNER TO {ROL_OWNER}', objeto.typname);
              END LOOP;
            END $$;
        """)

        # Privilegios sobre lo existente y sobre lo que cree vael_owner en migraciones futuras.
        dml = "SELECT, INSERT, UPDATE, DELETE"
        await conexion.execute(f"GRANT {dml} ON ALL TABLES IN SCHEMA public TO {ROL_APP}, {ROL_SYSTEM}")
        await conexion.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROL_APP}, {ROL_SYSTEM}")
        await conexion.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {ROL_OWNER} IN SCHEMA public "
            f"GRANT {dml} ON TABLES TO {ROL_APP}, {ROL_SYSTEM}"
        )
        await conexion.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {ROL_OWNER} IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {ROL_APP}, {ROL_SYSTEM}"
        )
        # La tabla de versiones de Alembic solo la toca vael_owner.
        existe_versiones = await conexion.fetchval("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        if existe_versiones:
            await conexion.execute(f"REVOKE ALL ON public.alembic_version FROM {ROL_APP}, {ROL_SYSTEM}")
    finally:
        await conexion.close()


async def _main() -> None:
    owner_url = make_url(settings.database_owner_url)
    if not owner_url.database:
        raise SystemExit("DATABASE_OWNER_URL no indica la base de datos")
    await crear_roles(
        url_admin(),
        owner_url.database,
        app=_credencial(settings.database_url, ROL_APP, "DATABASE_URL"),
        system=_credencial(settings.database_system_url, ROL_SYSTEM, "DATABASE_SYSTEM_URL"),
        owner=_credencial(settings.database_owner_url, ROL_OWNER, "DATABASE_OWNER_URL"),
    )
    print(f"Roles {ROL_OWNER}, {ROL_APP} y {ROL_SYSTEM} listos en la base {owner_url.database}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(_main())
