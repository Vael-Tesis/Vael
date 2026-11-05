> COPIA del documento del Drive `VAEL/Docs/16_requerimientos_admin.md`, versión 1.6 — **APROBADO** (2026-10-18); estado actualizado el 2026-11-04, copiada el 2026-11-04.
> La fuente de verdad es el Drive. No editar aquí: los cambios se hacen en el Drive y se vuelven a copiar.

# 16 — Requerimientos funcionales del perfil Admin RRHH

| Campo | Valor |
|---|---|
| Versión | 1.6 — **APROBADO** (2026-10-18); estado actualizado el 2026-11-04 |
| Tarea de origen | PLN-A-03 |
| Fuentes | Monografía, sección 1.3; doc 15 (matriz); DEC-007 a DEC-024 |
| Backlog | Cada requerimiento corresponde a una historia de usuario del Product Backlog (`VAEL/Docs/Scrum`) |
| Se ejecutan en | HU-25, tarea TST-A-01 (resultado y observaciones de cada RF). Registro: `docs/validacion/rf_admin.md` en el repositorio |

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
| RF-A-10 | HU-12 | Consultar el análisis | Muestra puntaje, clasificación, resumen, habilidades, inconsistencias y justificación; muestra el desglose por criterio ponderado con su justificación (DEC-024), o "análisis anterior al desglose" si es anterior a esa decisión; nunca datos de emociones | 1 | OE2 |
| RF-A-11 | HU-15 | Confirmar o revertir recomendaciones | Confirmación individual o en lote; una decisión contraria exige justificación; avance → correo de la etapa siguiente; descarte → un único correo de cierre; ningún correo sale sin decisión | 1 | **OE3**, OE1 |
| RF-A-12 | HU-16 | Consultar el historial de decisiones | Cada decisión muestra etapa, recomendación, puntaje, umbral, decisión, autor, fecha y justificación; ninguna se edita ni se borra | 1 | **OE3** |
| RF-A-13 | HU-13 | Notas y etiquetas | Se agregan, editan y eliminan notas propias (autor y fecha); se asignan y quitan etiquetas; el listado se filtra por etiqueta | 1 | — |
| RF-A-14 | HU-17 | Consultar el ranking | Ordena por `score_final` (DEC-007) con desglose; los procesos incompletos aparecen aparte | 2 | — |
| RF-A-15 | HU-18 | Decidir finalistas | Marcar finalistas o descartar, individual o en lote, por el endpoint de decisiones, con los mismos registros y correos de RF-A-11. El lote solo acepta las decisiones que coinciden con la recomendación por `top_candidatos_finalistas`; los empatados con el puntaje del último puesto también reciben `avanzar`, y sin `score_final` no hay recomendación ni lote (DEC-022) | 2 | OE3 |
| RF-A-16 | HU-19 | Revisar las evaluaciones | Detalle del examen, detalle de la entrevista (transcripción, dimensiones, capturas) y auditoría con semáforo | 2 | — |
| RF-A-17 | HU-14 | Banco de talento | Lista solo a los candidatos que RRHH marcó explícitamente (`en_banco_talento`), con filtro por área en el backend y por puntaje en la pantalla; un candidato puede enviarse al banco desde su detalle; una empresa no ve los del banco de otra | 2 | — |
| RF-A-18 | HU-07 | Gestionar usuarios | El admin crea usuarios (credenciales por correo), los activa, desactiva, cambia su contraseña y reenvía credenciales; listar lo ven admin y gerente; desactivar invalida la sesión al instante | 2 | — |
| RF-A-19 | HU-20 | Consultar el dashboard | Vacantes y candidatos por estado, recomendaciones pendientes por etapa, postulaciones por día, minutos promedio de revisión (OE1) y tasa de concordancia (M-02), con filtro `desde`/`hasta`; una empresa no ve las cifras de otra | 2 | OE1 |
| RF-A-20 | HU-04 | Aislar los datos de cada empresa | Un usuario de la empresa A no ve ni modifica datos de la empresa B por ninguna pantalla ni endpoint | 2 | **OE4** |

## Criterio del hito H-50 (DEC-006) — aprobado

**H-50 se alcanza al cierre del Sprint 1 cuando:**
1. La historia técnica HU-21 (base común) está completa, y
2. **RF-A-01 a RF-A-13 están en verde**, ejecutados contra el backend real con los datos semilla del doc 13.

### Estado al cierre del Sprint 1 (2026-10-27)

| RF | Implementado en | Pruebas automáticas (190 en verde en el CI) |
|---|---|---|
| RF-A-01, RF-A-02 | DEV-A-02 · PR #18 | `test_sesiones.py` |
| RF-A-03 | DEV-A-02 · PR #18 | `test_permisos_por_rol.py` (recorre todas las rutas de escritura y exige 403 al evaluador) |
| RF-A-04 | DEV-A-01 · PR #17, DEV-A-03 · PR #19 | `test_areas.py`, `test_notas_etiquetas_areas.py` |
| RF-A-05 | DEV-A-03 · PR #19 | `test_plantillas.py` |
| RF-A-06, RF-A-07, RF-A-08 | DEV-A-04 · PR #20 | `test_vacantes.py` |
| RF-A-09, RF-A-10 | DEV-A-05 · PR #21 | `test_registro_candidatos.py`, `test_sin_emociones.py` |
| RF-A-11, RF-A-12 | DEV-C-10 · PR #13, DEV-A-05 · PR #21 | `test_decisiones.py`, `test_invariante_decisiones.py` |
| RF-A-13 | DEV-A-01 · PR #17, DEV-C-05 · PR #12, DEV-A-05 · PR #21 | `test_notas_etiquetas_areas.py`, `test_candidato_tags.py` |

HU-21 (base técnica) está completa: DEV-C-01, 03, 04, 05, 06, 07/08, 09, 10, 11, 12 y 13 (en modo en proceso) y TST-C-03 integradas (PR #4 a #16).

**Lo que falta para declarar H-50:** ejecutar RF-A-01 a RF-A-13 **contra el backend real con los datos semilla**, en el navegador, y registrar el resultado (TST-A-01). Hasta ahora hay pruebas automáticas y una prueba de humo por HTTP (login, vacantes, bandeja, etiquetas, rotación y reutilización del refresh token, logout), pero no una verificación visual.

### Prueba manual en curso (TST-A-01, 2026-10-28)

El Product Owner empezó la prueba en el navegador con el entorno local. **El resultado formal por requerimiento aún no está registrado**, así que H-50 sigue sin declararse. Lo observado hasta ahora:

| RF | Observación | Resultado |
|---|---|---|
| RF-A-07 | No había forma de ver ni copiar el enlace de postulación de una vacante publicada | Corregido (PR #23): enlace copiable en la pestaña Publicación |
| RF-A-09 | La postulación pública respondía 500 sin mensaje: en local no había S3 | Corregido (PR #23): validación del PDF, error 502 claro y S3 local (DEC-023) |
| RF-A-10 | Un CV real de prueba se analizó con Gemini: puntaje, clasificación y resumen coherentes, sin datos de emociones. Tardó 5 minutos por la saturación de Google | Funciona; tiempo límite y reintento ante 504 agregados (PR #23) |
| RF-A-11 | El correo de cierre llegó a la bandeja local (Mailpit) tras la decisión en la Bandeja | Funciona |
| RF-A-18 (Sprint 2) | Cambiar contraseña usaba el diálogo del navegador | Corregido (PR #23): modal |

**Esqueleto en AWS (HU-22):** desplegado y verificado el 2026-10-28 (PR #24); RF-A-01 comprobado en AWS (200 / 401 / 403 con usuario inactivo).

### Verificación en el navegador del Sprint 2 (DEV-A-06 a DEV-A-10, 2026-10-29 a 2026-10-31)

| RF | Observación | Resultado |
|---|---|---|
| RF-A-14 | Con los candidatos de proceso completo de TI-2026-001 (doc 13, DEV-A-07): el ranking muestra siete candidatos ordenados por `score_final` (18.44 a 12.48) y uno con proceso incompleto aparte, sin puesto | Funciona (verificado en el navegador) |
| RF-A-15 | Con el mismo conjunto: los cinco primeros del ranking (`top_candidatos_finalistas` = 5) muestran la recomendación "Finalista" y los dos últimos "Fuera del corte"; se confirmó en vivo al primero como finalista (`POST /candidatos/{id}/decision`) y su estado pasó a `finalista` al recargar. La regla de empates y el rechazo del lote contrario siguen cubiertos por las pruebas automáticas de DEV-A-06 (`test_decisiones.py`, `test_ranking.py`) | Funciona (verificado en el navegador y con pruebas automáticas) |
| RF-A-16 | Con el mismo conjunto: P-11 lista los ocho exámenes con semáforo verde, amarillo y rojo representados; P-12 muestra sus eventos de auditoría en la misma vista (sin preguntas para estos candidatos semilla, ver doc 13); P-13 y P-14 muestran las cinco dimensiones de la plantilla Técnico Estándar con su comentario y la transcripción; P-15 agrupa los eventos de examen y de entrevista por candidato | Funciona (verificado en el navegador). No se pudo probar la galería de capturas con una imagen real: los candidatos semilla no tienen `capturas_auditoria` (alcance de DEV-A-07, ver doc 13) |
| RF-A-19 | `GET /metricas/dashboard` probado con `admin@andina.example.com` (8 candidatos de TI-2026-001, incluido el finalista de la prueba de DEV-A-07: minutos promedio de revisión 0.4, tasa de concordancia 100%) y con `admin@pacifico.example.com` (3 candidatos, cifras completamente distintas); el filtro `desde`/`hasta` con una fecha futura deja las postulaciones y las dos métricas de decisiones vacías, sin tocar las fotografías de estado. Cubierto además con 5 pruebas automáticas, incluida la de aislamiento por tenant exigida en el CA | Funciona (verificado en el navegador y con pruebas automáticas) |
| RF-A-18 | Con `admin@andina.example.com`: se desactivó a un usuario activo y, con su access token vigente (obtenido antes de desactivarlo) ya en mano, la siguiente petición pasó de 200 a 401 al instante, sin esperar a que expirara; se reactivó, se creó un usuario nuevo (correo de credenciales recibido en Mailpit), se le reenviaron credenciales (segundo correo) y se le cambió la contraseña con el modal existente. Con `gerente@andina.example.com`: la lista se ve sin el botón "Nuevo usuario" ni el menú de acciones en ninguna fila. El CA explícito (token rechazado tras desactivar) ya estaba cubierto por `test_sesiones.py::test_desactivar_o_cambiar_la_contrasena_invalida_los_tokens_al_instante` desde DEV-A-02 (DEC-011); no se duplicó la prueba | Funciona (verificado en el navegador; CA cubierto por una prueba automática existente) |
| RF-A-17 | `Candidato.en_banco_talento` (migración `b7c8d9e0f1a2`, aplica y revierte limpio contra PostgreSQL) reemplaza la inferencia anterior por clasificación de la IA y estado de descarte. Probado con `admin@andina.example.com`: P-18 arrancó vacía; desde el detalle de Álvaro Medina Ponce (TI-2026-001) se usó "Enviar al banco de talento" y el botón pasó a "En el banco de talento"; P-18 lo mostró con su área y vacante anterior; el filtro por área lo ocultó y lo volvió a mostrar correctamente. Con `admin@pacifico.example.com` el selector de área solo listó la suya y no se vio a Álvaro — aislamiento por tenant confirmado en vivo además de con 6 pruebas automáticas, incluida la de aislamiento exigida en el CA | Funciona (verificado en el navegador y con pruebas automáticas) |

### Resultado de TST-A-01 (2026-11-01, PR #33)

El resultado formal por requerimiento está registrado en `docs/validacion/rf_admin.md` (commit base `113ac72`): **RF-A-01 a RF-A-20 en verde**, cada uno con las pruebas automáticas que lo cubren. Para cerrarlo se agregaron las pruebas que faltaban (RF-A-10, RF-A-12, RF-A-16 y RF-A-18), y RF-A-12 se reforzó en la base de datos: `vael_app` y `vael_system` ya no pueden editar ni borrar filas de `decisiones_candidato` (migración `c8d9e0f1a2b3`).

Las dos partes de un criterio que solo se podían ver en el navegador, la redirección al dashboard (RF-A-01) y la renovación transparente de la sesión (RF-A-02), las cubre la prueba E2E con Playwright contra el backend y el frontend reales con los datos semilla (TST-A-03 · PR #34, DEC-020), que corre en el CI. Según el registro, **no quedan verificaciones manuales pendientes.**

| RF | Implementado en (Sprint 2) |
|---|---|
| RF-A-14, RF-A-15 | DEV-A-06 · PR #27 (ranking y recomendación de finalistas, DEC-022) |
| RF-A-16 | DEV-A-07 · PR #28 |
| RF-A-17 | DEV-A-08 · PR #31 |
| RF-A-18 | DEV-A-09 · PR #30 |
| RF-A-19 | DEV-A-10 · PR #29 |
| RF-A-20 | TST-C-01 · PR #32 (77 de 77 endpoints autenticados cubiertos; 0 accesos cruzados) |

**H-50:** según el registro de TST-A-01, sus dos condiciones se cumplen desde el 2026-11-01: HU-21 completa y RF-A-01 a RF-A-13 en verde (pruebas automáticas sobre PostgreSQL, más la E2E contra el backend y el frontend reales con los datos semilla). **Queda pendiente que el Product Owner lo declare.** Nota honesta: se cumplió después del cierre del Sprint 1 (2026-10-23), no al cierre como pedía el criterio.

## Criterio del perfil Admin al 100% (E3)

RF-A-01 a RF-A-20 en verde, la suite de aislamiento (TST-C-01) en verde y el perfil desplegado en AWS con el smoke test aprobado.

**Estado (2026-11-03):** las dos primeras condiciones se cumplen. Falta la tercera: el último despliegue en AWS (2026-10-29) tenía el código del Sprint 1, sin el trabajo del Sprint 2 (PR #27 a #34). Hay que volver a desplegar y repetir el smoke test.

## Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-14 | Borrador |
| 1.1 | 2026-10-18 | Aprobado; correspondencia con las historias de usuario y sus sprints; criterios ampliados con la retrospectiva (eliminar en borrador, eliminar áreas sin vacantes, guardar textos, editar y eliminar notas, enviar al banco) |
| 1.2 | 2026-10-27 | Estado al cierre del Sprint 1: RF-A-01 a RF-A-13 implementados con pruebas automáticas; falta la verificación con datos semilla en el navegador para declarar H-50 |
| 1.3 | 2026-10-28 | Avance de la prueba manual (TST-A-01) y observaciones corregidas en el PR #23; esqueleto en AWS desplegado (PR #24); H-50 aún sin declarar |
| 1.4 | 2026-11-03 | Resultado de TST-A-01: RF-A-01 a RF-A-20 en verde (PR #33) y E2E con Playwright (PR #34); RF-A-14 a RF-A-20 implementados en el Sprint 2; condiciones de H-50 cumplidas, pendiente su declaración; falta desplegar el Sprint 2 en AWS para el criterio de E3 |
| 1.5 | 2026-11-03 | CA de RF-A-15 con la regla de DEC-022 (recomendación por ranking, empates en el último puesto y candidatos sin `score_final`), como lo pide su sección "Consecuencias". TST-A-01 ya lo verificó con sus cuatro pruebas de DEC-022 (`docs/validacion/rf_admin.md`): sigue en verde |
| 1.6 | 2026-11-04 | Fusión con los borradores del Sprint 2: CA de RF-A-17 (marcado explícito y aislamiento), RF-A-18 (cambio de contraseña, listar admin y gerente) y RF-A-19 (detalle de cifras, filtro y aislamiento); CA de RF-A-10 con el desglose de DEC-024 (DEV-C-14 · PR #38); verificación en el navegador de RF-A-14 a RF-A-19; fuentes hasta DEC-024 |
