"""Alta de una empresa cliente y de su administrador inicial (DEC-015). No es un endpoint.

Uso:

    python -m app.scripts.crear_empresa --nombre "<razón social>" --admin-email <correo> \
        [--email-contacto <correo para consultas de datos personales>]

1. Calcula el `tenant_id` y crea la empresa.
2. Fija ese tenant en la sesión y crea al administrador con una contraseña temporal, como
   `vael_app` (sujeto a la RLS, DEC-010).
3. Envía las credenciales por correo. La contraseña nunca se imprime.
4. Es idempotente: si la empresa o el administrador ya existen, lo informa y no duplica.

El `tenant_id` se deriva de la razón social normalizada (UUID v5). Así el script reconoce una
empresa ya creada sin consultar las demás, que la RLS no le deja ver, y sin ampliar la lista
cerrada de la sesión del sistema.
"""
import argparse
import asyncio
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import con_tenant, sesion_con_tenant
from app.core.security import generate_temporary_password, hash_password
from app.models.usuario import Empresa, RolUsuario, Usuario
from app.services.correos import correo_credenciales_usuario

# Espacio de nombres fijo de VAEL para derivar los tenant_id (no cambiarlo: cambiaría todos).
ESPACIO_TENANTS = UUID("6f1c2a4e-9b7d-4e58-a3c1-0d5e7f9a2b64")

AbrirSesion = Callable[[str], AsyncSession]


class ErrorAlta(Exception):
    """El alta no se pudo completar; no se guardó nada."""


@dataclass(frozen=True)
class ResultadoAlta:
    tenant_id: str
    empresa: Empresa
    administrador: Usuario
    empresa_creada: bool
    administrador_creado: bool


def tenant_de(nombre: str) -> str:
    """tenant_id determinístico de una razón social (sin distinguir mayúsculas ni espacios)."""
    normalizado = re.sub(r"\s+", " ", nombre).strip().casefold()
    return str(uuid5(ESPACIO_TENANTS, normalizado))


async def crear_empresa(
    nombre: str,
    admin_email: str,
    *,
    email_contacto: str | None = None,
    admin_nombre: str = "Administrador",
    admin_apellidos: str | None = None,
    password: str | None = None,
    enviar_credenciales: bool = True,
    abrir_sesion: AbrirSesion = sesion_con_tenant,
) -> ResultadoAlta:
    """Crea (o reconoce) la empresa y su administrador inicial.

    `password` solo lo usa el script de semillas, que lee las contraseñas del entorno; sin
    él se genera una temporal y se envía por correo si `enviar_credenciales` es True.
    """
    nombre = re.sub(r"\s+", " ", nombre).strip()
    admin_email = admin_email.strip().lower()
    if not nombre or not admin_email:
        raise ErrorAlta("La razón social y el correo del administrador son obligatorios")
    tenant_id = tenant_de(nombre)

    with con_tenant(tenant_id):
        async with abrir_sesion(tenant_id) as db:
            empresa = (await db.exec(select(Empresa).where(Empresa.tenant_id == tenant_id))).first()
            empresa_creada = empresa is None
            if empresa is None:
                empresa = Empresa(tenant_id=tenant_id, nombre=nombre, email_contacto=email_contacto)
                db.add(empresa)

            administrador = (
                await db.exec(select(Usuario).where(Usuario.tenant_id == tenant_id, Usuario.email == admin_email))
            ).first()
            administrador_creado = administrador is None
            password_temporal: str | None = None
            if administrador is None:
                password_temporal = password or generate_temporary_password()
                administrador = Usuario(
                    tenant_id=tenant_id,
                    nombre=admin_nombre,
                    apellidos=admin_apellidos or nombre,
                    email=admin_email,
                    password_hash=await hash_password(password_temporal),
                    rol=RolUsuario.ADMIN,
                )
                db.add(administrador)

            try:
                await db.flush()
            except IntegrityError as exc:
                await db.rollback()
                raise ErrorAlta(f"El correo {admin_email} ya pertenece a un usuario de otra empresa") from exc

            # Se envía antes del commit: si el correo falla, no queda un administrador sin credenciales.
            if administrador_creado and enviar_credenciales and password is None:
                await correo_credenciales_usuario(administrador, password_temporal or "")
            await db.commit()

    return ResultadoAlta(tenant_id, empresa, administrador, empresa_creada, administrador_creado)


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Alta de una empresa cliente de VAEL (DEC-015)")
    parser.add_argument("--nombre", required=True, help="Razón social de la empresa")
    parser.add_argument("--admin-email", required=True, help="Correo del administrador inicial")
    parser.add_argument("--email-contacto", help="Contacto para consultas sobre datos personales (DEC-013)")
    parser.add_argument("--admin-nombre", default="Administrador")
    parser.add_argument("--admin-apellidos")
    return parser.parse_args(argv)


async def _main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        resultado = await crear_empresa(
            args.nombre,
            args.admin_email,
            email_contacto=args.email_contacto,
            admin_nombre=args.admin_nombre,
            admin_apellidos=args.admin_apellidos,
        )
    except ErrorAlta as error:
        print(f"No se creó nada: {error}", file=sys.stderr)
        return 1

    empresa = "creada" if resultado.empresa_creada else "ya existía"
    admin = "creado; credenciales enviadas por correo" if resultado.administrador_creado else "ya existía"
    print(f"Empresa {resultado.empresa.nombre} ({resultado.tenant_id}): {empresa}", file=sys.stderr)
    print(f"Administrador {resultado.administrador.email}: {admin}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
