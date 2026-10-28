# DEC-012 — Redis (ElastiCache) fuera del alcance

| Campo | Valor |
|---|---|
| Estado | Aprobada |
| Fecha | 2026-10-13 |
| Tarea de origen | PLN-C-02 (decisión 5) |
| Decidido por | Equipo (Gabriel Llanos, Diego Nina) |
| Reemplaza | Docs 03 y 04: ElastiCache Redis para sesiones, blacklist de tokens y caché de análisis |
| Depende de | DEC-011 (sesiones en PostgreSQL) |

## Contexto

- **HECHO (código):** no existe ninguna integración con Redis. El endpoint de logout documenta que no invalida tokens por la falta de Redis.
- **HECHO (documentación):** los docs 03 y 04 asignan a Redis tres funciones: sesiones activas, blacklist de tokens en el logout y caché de resultados del análisis de CV.
- Con DEC-011, las sesiones y la revocación se resuelven en PostgreSQL.

## Decisión

Redis y ElastiCache quedan fuera del alcance del proyecto. Cada función prevista se resuelve así:

| Función prevista | Resolución |
|---|---|
| Sesiones activas | Tabla `sesiones` en PostgreSQL (DEC-011) |
| Blacklist de tokens en el logout | Revocación del refresh token y `token_version` (DEC-011) |
| Caché del análisis de CV | No se necesita: el resultado ya se persiste en el registro del candidato y no se recalcula en cada consulta |

## Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| ElastiCache Redis para la blacklist y las sesiones | Agrega un servicio que operar, asegurar y pagar, sin resolver un problema que PostgreSQL no resuelva a la escala del proyecto |
| Redis local solo en desarrollo | Crearía una diferencia entre los entornos de desarrollo y producción |

## Trade-off aceptado

Cada petición autenticada consulta PostgreSQL para validar al usuario y su `token_version`. A la escala del proyecto, este costo se considera despreciable; es una **hipótesis** que se contrasta con las métricas de latencia de la etapa de Testing. Si en el futuro la carga lo justificara, Redis puede incorporarse como caché sin cambiar el modelo de datos.

## Consecuencias

Documentos a actualizar:
- Doc 03: eliminar ElastiCache de la capa de datos del diagrama.
- Doc 04: eliminar Redis de las tablas de base de datos e infraestructura.
- Doc 06: eliminar la referencia a la blacklist en Redis de `/auth/logout`.
- Doc 09: eliminar ElastiCache del aprovisionamiento.
- Roadmap: decisión 5 de PLN-C-02 cerrada; ElastiCache excluido de la topología de DEP-C-02.

## Validación

- Ninguna dependencia de Redis en `requirements.txt`, `docker-compose.yml` ni en la infraestructura aprovisionada.
- Las pruebas de logout y revocación de DEC-011 pasan sin Redis.
