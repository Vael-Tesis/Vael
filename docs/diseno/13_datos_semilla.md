> COPIA del documento del Drive `VAEL/Docs/13_datos_semilla.md`, versión 1.1 — **APROBADO** (2026-10-18), copiada el 2026-10-18.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 13 — Datos semilla

| Campo | Valor |
|---|---|
| Versión | 1.1 — **APROBADO** (2026-10-18) |
| Tarea de origen | PLN-C-05 |
| Implementación | Historia HU-21, tarea DEV-C-03 (script idempotente) |
| Usado por | TST-C-01 (OE4), TST-A-04 (OE1), TST-A-05 (OE2), TST-A-03 (pruebas de extremo a extremo), demo de E3 |

## Reglas

1. **Ningún dato personal real.** Nombres, empresas, teléfonos y trayectorias son ficticios. Los correos usan el dominio reservado `example.com` (RFC 2606), que no puede recibir correo real.
2. **Ninguna contraseña en el repositorio.** El script lee las contraseñas de los usuarios semilla desde variables de entorno (`SEED_PASSWORD_*`).
3. **Idempotente.** Ejecutar el script dos veces no duplica registros: busca por claves naturales (`codigo` de vacante, `email` de usuario, `codigo_corto` de área).
4. **Cada dato tiene un propósito de prueba.**
5. **Las empresas se crean con el script de alta** (`app.scripts.crear_empresa`, DEC-015); el script de semillas lo reutiliza.

## Empresas (aprobadas)

| Empresa | Uso |
|---|---|
| **Empresa A — Andina Servicios S.A.C.** (ficticia) | Empresa principal: pruebas funcionales, métricas y demo |
| **Empresa B — Pacífico Logística S.A.C.** (ficticia) | Empresa testigo para TST-C-01: tiene datos propios que la empresa A nunca debe ver ni modificar |

Antes de usarlos en una presentación pública, conviene verificar en SUNAT que no coinciden con una razón social real.

## Usuarios

Empresa A (un usuario por rol, para la matriz de permisos de TST-A-02):

| Rol | Correo |
|---|---|
| admin | `admin@andina.example.com` |
| reclutador | `reclutador@andina.example.com` |
| evaluador | `evaluador@andina.example.com` |
| gerente | `gerente@andina.example.com` |
| reclutador **inactivo** | `inactivo@andina.example.com` (prueba de RF-A-01: login rechazado con 403) |

Empresa B: `admin@pacifico.example.com` y `reclutador@pacifico.example.com`.

## Áreas

| Empresa | Nombre | Código | Instrucción de IA |
|---|---|---|---|
| A | Tecnología | TI | Valorar la profundidad técnica demostrable y los proyectos verificables |
| A | Comercial | VEN | Valorar la experiencia en ventas, el logro de metas y la comunicación |
| A | Operaciones | OPE | Valorar la experiencia en procesos, logística y mejora continua |
| B | Logística | LOG | — |

## Plantillas de evaluación (empresa A)

Las cuatro plantillas predefinidas del doc 05: Técnico Estándar, Comercial, Liderazgo y Creativo. En los tests se agrega una plantilla **inválida a propósito** (pesos que suman 90) para probar la validación.

## Vacantes

| Código | Empresa | Título | Nivel | Estado | Plantilla | Propósito |
|---|---|---|---|---|---|---|
| TI-2026-001 | A | Desarrollador Backend Python | semi_senior | abierta | Técnico Estándar | Flujo principal, OE1, OE2, demo |
| VEN-2026-001 | A | Ejecutivo Comercial | junior | abierta | Comercial | Segundo perfil de evaluación |
| OPE-2026-001 | A | Analista de Operaciones | junior | borrador | — | Estados de vacante y eliminación en borrador |
| TI-2026-002 | A | Desarrollador Frontend (confidencial) | junior | abierta, confidencial | Técnico Estándar | No debe aparecer en el listado público ni en el feed XML |
| LOG-2026-001 | B | Coordinador Logístico | semi_senior | abierta | — | Datos de la empresa testigo |

## Currículums ficticios (20, empresa A)

Se generan como PDF en `backend/seeds/cvs/` **con un script a partir de plantillas de texto**, para que sean reproducibles (forma de generación propuesta; se confirma al implementar DEV-C-03).

### TI-2026-001 — Desarrollador Backend Python (12 CVs)

| ID | Perfil | Resultado esperado | Propósito |
|---|---|---|---|
| CV-TI-01 | 5 años con Python, FastAPI y PostgreSQL | Score alto → avanzar | Positivo claro; **referencia OE2** |
| CV-TI-02 | 4 años con Django y MySQL | Score alto | Tecnología relacionada |
| CV-TI-03 | 3 años con Python y proyectos en GitHub | Medio-alto | Evidencia verificable |
| CV-TI-04 | 2 años con Java y algo de Python | Cercano al umbral (≈60) | **Caso límite; referencia OE2** |
| CV-TI-05 | Recién egresado con prácticas en Python | Cercano al umbral | Límite por experiencia |
| CV-TI-06 | 6 años con PHP, sin Python | Bajo → descartar | Experiencia sin match |
| CV-TI-07 | Diseñador gráfico sin experiencia técnica | Muy bajo | Negativo claro; **referencia OE2** |
| CV-TI-08 | 5 años con Python, con un vacío de 14 meses | Alto con inconsistencia | Detección de inconsistencias |
| CV-TI-09 | Fechas laborales superpuestas | Inconsistencias detectadas | Coherencia del CV |
| CV-TI-10 | Líder técnico, 12 años | Alto | Sobrecalificación |
| CV-TI-11 | PDF escaneado como imagen | Revisión manual | Ruta de error de extracción |
| CV-TI-12 | PDF dañado | Error controlado | Reporte de fallidos (RF-A-09) |

### VEN-2026-001 — Ejecutivo Comercial (8 CVs)

| ID | Perfil | Propósito |
|---|---|---|
| CV-VEN-01 a CV-VEN-03 | Experiencia comercial con metas cumplidas | Positivos |
| CV-VEN-04 y CV-VEN-05 | Atención al cliente, sin ventas | Casos límite |
| CV-VEN-06 | Desarrollador de software | Negativo frente a la instrucción del área |
| CV-VEN-07 | Sin experiencia laboral | Negativo |
| CV-VEN-08 | Perfil comercial con LinkedIn y portafolio | Extracción de enlaces |

## Muestras para las métricas (aprobadas)

| Métrica | Muestra |
|---|---|
| OE1 (etapa de CV) | CV-TI-01 a CV-TI-10 (sin los PDF con fallas) |
| OE2 | CV-TI-01, CV-TI-04 y CV-TI-07, 10 ejecuciones cada uno (30 llamadas a Gemini) |

## Datos de la empresa B

Un área, una vacante, 3 candidatos con su análisis, un examen y una nota interna: cubren cada tipo de recurso al que un endpoint de la empresa A podría intentar acceder en TST-C-01.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador |
| 1.1 | 2026-10-18 | Aprobado: nombres de las empresas, muestras de OE1 y OE2; alta de empresas con el script de DEC-015; vacante en borrador usada también para la eliminación |
