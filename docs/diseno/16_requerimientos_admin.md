> COPIA del documento del Drive `VAEL/Docs/16_requerimientos_admin.md`, versión 1.1 — **APROBADO** (2026-10-18), copiada el 2026-10-18.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 16 — Requerimientos funcionales del perfil Admin RRHH

| Campo | Valor |
|---|---|
| Versión | 1.1 — **APROBADO** (2026-10-18) |
| Tarea de origen | PLN-A-03 |
| Fuentes | Monografía, sección 1.3; doc 15 (matriz); DEC-007 a DEC-019 |
| Backlog | Cada requerimiento corresponde a una historia de usuario del Product Backlog (`VAEL/Docs/Scrum`) |
| Se ejecutan en | HU-25, tarea TST-A-01 (resultado y observaciones de cada RF) |

Cada requerimiento tiene un criterio de aceptación (CA) verificable con los datos semilla del doc 13.

## Requerimientos

| ID | HU | Requerimiento | Criterio de aceptación | Sprint | Objetivo |
|---|---|---|---|---|---|
| RF-A-01 | HU-01 | Iniciar sesión | Con credenciales válidas ingresa al dashboard; inválidas → 401; usuario inactivo → 403 | 1 | — |
| RF-A-02 | HU-02 | Mantener y cerrar la sesión | La sesión se renueva sin intervención mientras el refresh token es válido; tras el logout ese refresh token se rechaza; al desactivar al usuario sus tokens dejan de servir | 1 | — |
| RF-A-03 | HU-03 | Controlar el acceso por rol | Cada rol accede solo a lo definido en el doc 15; el evaluador no crea ni decide; el backend rechaza con 403 aunque se intente fuera de la interfaz | 1 | — |
| RF-A-04 | HU-05 | Gestionar áreas | Admin y gerente crean, editan, activan y desactivan áreas; código corto único; un área con vacantes no se elimina | 1 | — |
| RF-A-05 | HU-06 | Gestionar plantillas | Se crean y editan plantillas con dimensiones; si los pesos no suman 100, se rechaza con un mensaje claro | 1 | — |
| RF-A-06 | HU-08 | Crear y editar vacantes | Se crea en borrador con código `{AREA}-{AÑO}-{NNN}` automático; una vacante en borrador puede eliminarse | 1 | — |
| RF-A-07 | HU-09 | Cambiar el estado de una vacante | Publicar, pausar, cerrar y duplicar funcionan; solo una vacante abierta acepta postulaciones; duplicar crea un borrador con código nuevo | 1 | — |
| RF-A-08 | HU-10 | Textos de difusión con IA | Se generan, editan y guardan; si la IA falla, se muestra un error sin bloquear la vacante | 1 | — |
| RF-A-09 | HU-11 | Registrar candidatos | El registro manual y la carga masiva crean candidatos y disparan su análisis; la carga masiva informa qué archivos fallaron y por qué | 1 | — |
| RF-A-10 | HU-12 | Consultar el análisis | Muestra puntaje, clasificación, resumen, habilidades, inconsistencias y justificación; nunca datos de emociones | 1 | OE2 |
| RF-A-11 | HU-15 | Confirmar o revertir recomendaciones | Confirmación individual o en lote; una decisión contraria exige justificación; avance → correo de la etapa siguiente; descarte → un único correo de cierre; ningún correo sale sin decisión | 1 | **OE3**, OE1 |
| RF-A-12 | HU-16 | Consultar el historial de decisiones | Cada decisión muestra etapa, recomendación, puntaje, umbral, decisión, autor, fecha y justificación; ninguna se edita ni se borra | 1 | **OE3** |
| RF-A-13 | HU-13 | Notas y etiquetas | Se agregan, editan y eliminan notas propias (autor y fecha); se asignan y quitan etiquetas; el listado se filtra por etiqueta | 1 | — |
| RF-A-14 | HU-17 | Consultar el ranking | Ordena por `score_final` (DEC-007) con desglose; los procesos incompletos aparecen aparte | 2 | — |
| RF-A-15 | HU-18 | Decidir finalistas | Marcar finalistas o descartar, individual o en lote, por el endpoint de decisiones, con los mismos registros y correos de RF-A-11 | 2 | OE3 |
| RF-A-16 | HU-19 | Revisar las evaluaciones | Detalle del examen, detalle de la entrevista (transcripción, dimensiones, capturas) y auditoría con semáforo | 2 | — |
| RF-A-17 | HU-14 | Banco de talento | Lista candidatos de procesos anteriores con filtros por área y puntaje; un candidato puede enviarse al banco desde su detalle | 2 | — |
| RF-A-18 | HU-07 | Gestionar usuarios | El admin crea usuarios (credenciales por correo), los activa, desactiva y reenvía credenciales; desactivar invalida la sesión al instante | 2 | — |
| RF-A-19 | HU-20 | Consultar el dashboard | Vacantes y candidatos por estado, recomendaciones pendientes, minutos promedio de revisión y tasa de concordancia | 2 | OE1 |
| RF-A-20 | HU-04 | Aislar los datos de cada empresa | Un usuario de la empresa A no ve ni modifica datos de la empresa B por ninguna pantalla ni endpoint | 2 | **OE4** |

## Criterio del hito H-50 (DEC-006) — aprobado

**H-50 se alcanza al cierre del Sprint 1 cuando:**
1. La historia técnica HU-21 (base común) está completa, y
2. **RF-A-01 a RF-A-13 están en verde**, ejecutados contra el backend real con los datos semilla del doc 13.

## Criterio del perfil Admin al 100% (E3)

RF-A-01 a RF-A-20 en verde, la suite de aislamiento (TST-C-01) en verde y el perfil desplegado en AWS con el smoke test aprobado.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador |
| 1.1 | 2026-10-18 | Aprobado; correspondencia con las historias de usuario y sus sprints; criterios ampliados con la retrospectiva (eliminar en borrador, eliminar áreas sin vacantes, guardar textos, editar y eliminar notas, enviar al banco) |
