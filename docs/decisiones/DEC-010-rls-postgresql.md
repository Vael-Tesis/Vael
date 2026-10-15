# DEC-010 — Aislamiento multiempresa en dos capas: aplicación + RLS en PostgreSQL

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión adicional derivada del hallazgo COH-07) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Complementa | Doc 03, "Multi-tenancy": modelo pool con aislamiento solo a nivel de aplicación |
| Relacionada con | OE4; TST-C-01; DEC-009 (la tabla `decisiones_candidato` también queda protegida) |

## Contexto

- **HECHO (código, 2026-10-13):** el aislamiento entre empresas se implementa solo en la aplicación: 28 consultas filtran por `tenant_id` y unos 20 accesos `db.get(...)` comparan el tenant de forma manual. La revisión no encontró accesos cruzados, pero cada consulta nueva depende de que el desarrollador recuerde el filtro.
- **HECHO (monografía E2 v1.1):** la Tabla 2.7 y la sección 2.4 justifican la elección de PostgreSQL por su seguridad a nivel de fila nativa, presentada como "segunda línea de defensa frente a errores en el código de la aplicación". La sección 2.3.5 deja la elección del nivel de aislamiento para el Capítulo III.
- **HECHO (entornos):** `docker-compose` y el CI se conectan a PostgreSQL con un usuario superusuario, y los superusuarios ignoran las políticas de RLS. Además, los tests actuales corren sobre SQLite, que no soporta RLS.

## Decisión

Se mantiene el modelo **pool** (tablas compartidas con `tenant_id`) y se aplica el aislamiento en dos capas.

1. **Capa de aplicación (se conserva):** todas las consultas siguen filtrando por `tenant_id`.
2. **Capa de base de datos (nueva):** cada tabla con `tenant_id` tiene RLS habilitada y forzada, con una política única:

   ```sql
   ALTER TABLE <tabla> ENABLE ROW LEVEL SECURITY;
   ALTER TABLE <tabla> FORCE ROW LEVEL SECURITY;
   CREATE POLICY aislamiento_tenant ON <tabla>
     USING (tenant_id = current_setting('app.tenant_id', true))
     WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
   ```

   Si `app.tenant_id` no está definido, ninguna fila es visible ni modificable: el sistema falla de forma segura.
3. **Roles de base de datos:**

   | Rol | Uso | Atributos |
   |---|---|---|
   | `vael_owner` | Migraciones de Alembic | Dueño de las tablas |
   | `vael_app` | Peticiones normales del backend y workers asíncronos | `NOSUPERUSER`, `NOBYPASSRLS`; solo privilegios DML |
   | `vael_system` | Lista cerrada de operaciones que cruzan empresas | `BYPASSRLS` |

4. **Contexto del tenant por transacción:** el `tenant_id` del JWT se guarda en un `contextvar` por petición, y un evento `after_begin` de SQLAlchemy ejecuta `SELECT set_config('app.tenant_id', :tenant_id, true)` al inicio de **cada** transacción. Así el valor no se pierde tras un `commit` ni se filtra entre peticiones que reutilizan conexiones del pool.
5. **Lista cerrada de operaciones del sistema** (sesión con `vael_system`):
   - Login: búsqueda del usuario por correo antes de conocer su empresa.
   - Postulación pública por código de vacante.
   - Listado público de vacantes abiertas y no confidenciales.

   Cualquier operación nueva que necesite cruzar empresas requiere un ADR propio.
6. **Workers asíncronos:** reciben el `tenant_id` en el mensaje de la cola y usan la sesión normal (`vael_app`) con ese tenant fijado.

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| A. Aislamiento solo en la aplicación | La seguridad depende de que ningún desarrollador olvide un filtro; deja sin sustento la justificación de PostgreSQL entregada en el E2 |
| C. Esquema o base de datos por empresa (bridge / silo) | Mayor costo y complejidad operativa (sección 2.3.5); las migraciones se multiplican por la cantidad de empresas; no se justifica a la escala del proyecto |

## Trade-off aceptado

- Mayor complejidad de configuración: tres roles, un evento por transacción y una sesión especial para la lista cerrada.
- Las operaciones de la lista cerrada quedan protegidas solo por la capa de aplicación; se compensa limitándolas a tres y verificándolo con un test.
- Costo de rendimiento esperado bajo, porque `tenant_id` ya está indexado en todas las tablas. Es una **hipótesis** que se verifica en las pruebas.

## Consecuencias

Cambios en el roadmap:

| Tarea | Cambio |
|---|---|
| DEV-C-11 (nueva) | Script de creación de roles, migración con las políticas en todas las tablas con `tenant_id`, `contextvar` + evento `after_begin`, sesión del sistema y su lista cerrada |
| TST-C-03 | Pasa a ser **prerrequisito** de DEV-C-11: los tests deben correr sobre PostgreSQL (el CI ya levanta el servicio; `conftest.py` deja de usar SQLite) |
| TST-C-01 | Incluye las pruebas de la capa de base de datos descritas abajo |
| `docker-compose`, CI y DEP-C-02 | Un script de inicialización crea los tres roles en cada entorno; en RDS, el backend se conecta con `vael_app` desde Secrets Manager |
| DEV-C-10 (DEC-009) | La tabla `decisiones_candidato` nace con su política de RLS |

Documentos a actualizar:
- Doc 03: sección "Multi-tenancy" (dos capas, roles y lista cerrada).
- Doc 05: nota de RLS en las tablas y política estándar.
- Doc 09: roles de base de datos, script de inicialización y variables de conexión por rol.
- `CLAUDE.md`: reglas sobre la sesión del sistema y la prohibición de conectarse como superusuario.
- Monografía, Capítulo III: justificar el modelo pool en dos capas con las alternativas descartadas.

## Validación

- **Prueba central del OE4:** con el tenant A fijado, `select(Candidato)` sin ningún filtro devuelve solo filas de A, aunque existan filas de B.
- Sin tenant fijado, cualquier consulta con `vael_app` devuelve cero filas.
- Un `INSERT` con `tenant_id` de otra empresa es rechazado por `WITH CHECK`.
- Tras un `commit` dentro de la misma petición, la siguiente transacción conserva el tenant correcto.
- Dos peticiones consecutivas de empresas distintas que reutilizan la misma conexión del pool no se mezclan.
- El usuario de la aplicación no es superusuario ni tiene `BYPASSRLS`.
- Solo los módulos de la lista cerrada importan la sesión del sistema.
