# Resultado de RF-A-01 a RF-A-20 — TST-A-01 (HU-25)

Registro del resultado de cada requerimiento funcional del perfil Admin RRHH (doc 16),
contra las pruebas automáticas del repositorio. Fecha: 2026-11-01. SHA del commit base:
`113ac72737c80d0d1df641979f2e66fe2b0eb6c8`.

**Cómo leer esta tabla:** "Pruebas automáticas" lista archivo::función; "Resultado" es
**Verde** (criterio cubierto y en verde) o **Rojo** (criterio sin cubrir u observación
abierta). Cuando una parte del criterio no es automatizable desde el backend (comportamiento
visual o de UX del frontend), se declara aparte en "Verificación manual" y no baja el
resultado a Rojo si el backend que la sostiene sí está verde — aunque, desde TST-A-03, esa
sección queda vacía: la prueba E2E con Playwright cubrió las dos partes que antes eran
manuales (RF-A-01, RF-A-02).

Tres criterios no tenían prueba automática antes de esta tarea y se agregaron:
**RF-A-10** (`test_consulta_analisis.py`), **RF-A-12** (ampliación de
`test_invariante_decisiones.py`) y **RF-A-16** y **RF-A-18** (`test_detalle_evaluaciones.py`
y ampliación de `test_sesiones.py`, respectivamente).

| RF | HU | Requerimiento | Criterio de aceptación | Pruebas automáticas | Resultado |
|---|---|---|---|---|---|
| RF-A-01 | HU-01 | Iniciar sesión | Credenciales válidas → dashboard; inválidas → 401; inactivo → 403 | `test_sesiones.py::test_login_valido_crea_la_sesion_y_un_access_de_15_minutos`, `test_credenciales_invalidas_401_y_usuario_inactivo_403`; `test_matriz_permisos.py::test_usuario_inactivo_no_inicia_sesion`; **E2E (TST-A-03):** `frontend/e2e/flujo-principal.spec.ts` — el paso "login → dashboard" navega de verdad en Chromium y confirma la redirección (antes, verificación manual) | **Verde** |
| RF-A-02 | HU-02 | Mantener y cerrar la sesión | Renovación sin intervención mientras el refresh es válido; logout rechaza ese refresh; desactivar invalida tokens | `test_sesiones.py::test_refresh_rota_el_token_y_revoca_el_anterior`, `test_reutilizar_un_refresh_revoca_todas_las_sesiones`, `test_tras_el_logout_el_refresh_de_esa_sesion_es_rechazado`, `test_desactivar_o_cambiar_la_contrasena_invalida_los_tokens_al_instante`; `test_matriz_permisos.py::test_matriz_logout_es_autenticado`; **E2E (TST-A-03):** `frontend/e2e/renovacion-sesion.spec.ts` — espera a que el access token expire de verdad (backend con `ACCESS_TOKEN_EXPIRE_MINUTES=2`) y confirma que la persona nunca ve el login: la petición original se reintenta sola tras `POST /auth/refresh` (antes, verificación manual) | **Verde** |
| RF-A-03 | HU-03 | Controlar el acceso por rol | Cada rol accede solo a lo del doc 15; el evaluador no crea ni decide; 403 aunque se intente fuera de la interfaz | `test_permisos_por_rol.py::test_el_evaluador_no_escribe`; `test_matriz_permisos.py::test_matriz_de_permisos` (258 casos, 4 roles × 62 endpoints + multipart y logout), `test_la_matriz_cubre_todos_los_endpoints_rrhh` | **Verde** |
| RF-A-04 | HU-05 | Gestionar áreas | Admin/gerente crean, editan, activan, desactivan; código corto único; área con vacantes no se elimina | `test_areas.py::test_crud_feliz_de_areas`, `test_reclutador_no_puede_crear_area`; `test_notas_etiquetas_areas.py::test_activar_y_desactivar_un_area`, `test_el_codigo_corto_es_unico_en_la_empresa`, `test_un_area_con_vacantes_no_se_elimina`, `test_permisos_de_areas` | **Verde** |
| RF-A-05 | HU-06 | Gestionar plantillas | Se crean y editan con dimensiones; pesos que no suman 100 se rechazan con mensaje claro | `test_plantillas.py::test_crud_feliz_de_plantillas_y_dimensiones`, `test_los_pesos_deben_sumar_100`, `test_reclutador_no_puede_crear_plantilla` | **Verde** |
| RF-A-06 | HU-08 | Crear y editar vacantes | Se crea en borrador con código `{AREA}-{AÑO}-{NNN}` automático; borrador se puede eliminar | `test_vacantes.py::test_se_crea_en_borrador_con_codigo_automatico`, `test_solo_se_elimina_en_borrador_y_sin_candidatos` | **Verde** |
| RF-A-07 | HU-09 | Cambiar el estado de una vacante | Publicar/pausar/cerrar/duplicar funcionan; solo abierta acepta postulaciones; duplicar crea borrador con código nuevo | `test_vacantes.py::test_los_cuatro_cambios_de_estado`, `test_solo_una_vacante_abierta_acepta_postulaciones` | **Verde** |
| RF-A-08 | HU-10 | Textos de difusión con IA | Se generan, editan y guardan; si la IA falla, error sin bloquear la vacante | `test_vacantes.py::test_los_textos_se_generan_editan_y_guardan`, `test_si_la_ia_falla_responde_502_sin_tocar_la_vacante` | **Verde** |
| RF-A-09 | HU-11 | Registrar candidatos | Registro manual y carga masiva crean candidatos y disparan su análisis; la carga masiva informa qué falló y por qué | `test_registro_candidatos.py::test_la_carga_masiva_informa_los_archivos_que_fallaron`, `test_un_error_de_s3_se_reporta_como_fallido`, `test_el_registro_manual_rechaza_un_pdf_danado`, `test_un_cv_escaneado_va_a_revision_manual_sin_llamar_a_la_ia`; `test_despacho.py::test_manejadores_reales_existen_para_cada_tipo` | **Verde** |
| RF-A-10 | HU-12 | Consultar el análisis | Muestra puntaje, clasificación, resumen, habilidades, inconsistencias y justificación; nunca emociones | `test_sin_emociones.py` (guarda estructural); **nuevo:** `test_consulta_analisis.py::test_el_detalle_del_candidato_muestra_el_analisis_completo_sin_emociones` (verifica el detalle de la API) | **Verde** |
| RF-A-11 | HU-15 | Confirmar o revertir recomendaciones | Individual o en lote; contraria exige justificación; avance → correo de etapa siguiente; descarte → único correo de cierre; ningún correo sin decisión | `test_decisiones.py::test_el_analisis_de_cv_deja_por_confirmar_sin_token_ni_correo`, `test_confirmar_avance_de_cv_emite_token_y_envia_correo`, `test_confirmar_descarte_envia_un_unico_correo_de_cierre_sin_puntajes`, `test_decision_contraria_sin_justificacion_responde_422`, `test_revertir_un_descarte_crea_fila_nueva_y_no_reenvia_el_cierre`, `test_el_lote_rechaza_decisiones_que_no_coinciden_y_no_ejecuta_ninguna`, `test_el_lote_confirma_las_decisiones_que_coinciden` | **Verde** |
| RF-A-12 | HU-16 | Consultar el historial de decisiones | Etapa, recomendación, puntaje, umbral, decisión, autor, fecha y justificación; ninguna se edita ni se borra | `test_decisiones.py::test_historial_y_detalle_muestran_las_decisiones`; `test_invariante_decisiones.py::test_el_proceso_completo_registra_el_100_por_ciento_de_las_decisiones`; `test_ninguna_decision_se_edita_ni_se_borra` (estático: ningún `db.delete` del código apunta a una decisión); **reforzado en la base de datos:** `test_vael_app_no_puede_editar_ni_borrar_decisiones` conecta como `vael_app` e intenta `UPDATE`/`DELETE` sobre una decisión existente (permission denied) y confirma que `SELECT`/`INSERT` siguen funcionando (migración `c8d9e0f1a2b3`, `crear_roles.py`) | **Verde** |
| RF-A-13 | HU-13 | Notas y etiquetas | Notas propias (autor y fecha); etiquetas asignadas/quitadas; listado filtrado por etiqueta | `test_notas_etiquetas_areas.py::test_crud_de_etiquetas`, `test_asignar_es_idempotente_y_quitar_responde_404_si_no_estaba`, `test_eliminar_la_etiqueta_borra_sus_asignaciones`, `test_solo_el_autor_edita_y_el_autor_o_un_admin_eliminan`, `test_no_se_asigna_una_etiqueta_de_otra_empresa`; `test_candidato_tags.py::test_listado_filtra_por_etiqueta` | **Verde** |
| RF-A-14 | HU-17 | Consultar el ranking | Ordena por `score_final` (DEC-007) con desglose; procesos incompletos aparte | `test_ranking.py::test_ranking_ordena_por_score_final_y_separa_los_procesos_incompletos`, `test_ranking_de_una_vacante_inexistente_responde_404` | **Verde** |
| RF-A-15 | HU-18 | Decidir finalistas | Marcar finalistas o descartar, individual o en lote, por el endpoint de decisiones, con los mismos registros y correos de RF-A-11 | `test_decisiones.py::test_entrevista_avanzar_marca_finalista_y_descartar_cierra`, `test_dec022_el_lote_avanza_a_los_primeros_del_ranking_y_descarta_al_resto`, `test_dec022_el_empate_en_el_ultimo_puesto_avanza_a_todos_los_empatados`, `test_dec022_sin_score_final_no_hay_recomendacion_ni_entra_en_el_lote`, `test_dec022_el_lote_rechaza_una_decision_que_no_coincide_con_el_ranking` | **Verde** |
| RF-A-16 | HU-19 | Revisar las evaluaciones | Detalle del examen, detalle de la entrevista (transcripción, dimensiones, capturas) y auditoría con semáforo | `test_auditoria_general.py` (4 pruebas), `test_registro_candidatos.py::test_la_bandeja_muestra_el_semaforo_del_examen`, `test_entrevista_lista.py`; **nuevo:** `test_detalle_evaluaciones.py::test_detalle_de_examen_incluye_sus_preguntas_y_respuestas`, `test_detalle_de_entrevista_incluye_transcripcion_dimensiones_y_capturas` | **Verde** |
| RF-A-17 | HU-14 | Banco de talento | Lista con filtros por área y puntaje; se envía desde el detalle del candidato | `test_banco_talento.py` (6 pruebas: marca idempotente, 404, filtro por marca, filtro por área, aislamiento entre empresas, permiso del evaluador) | **Verde** |
| RF-A-18 | HU-07 | Gestionar usuarios | Admin crea (credenciales por correo), activa, desactiva, reenvía credenciales; desactivar invalida la sesión al instante | `test_sesiones.py::test_desactivar_o_cambiar_la_contrasena_invalida_los_tokens_al_instante`; **nuevo:** `test_crear_usuario_envia_credenciales_y_el_usuario_puede_iniciar_sesion`, `test_reenviar_credenciales_invalida_la_sesion_anterior_y_la_nueva_contrasena_sirve`; `test_matriz_permisos.py` (niveles Admin / Admin o gerente de `/auth/usuarios*`) | **Verde** |
| RF-A-19 | HU-20 | Consultar el dashboard | Vacantes y candidatos por estado, recomendaciones pendientes, minutos promedio de revisión y tasa de concordancia | `test_metricas.py::test_una_empresa_no_ve_las_metricas_de_otra`, `test_oe1_y_m02_se_calculan_sobre_las_decisiones_del_tenant`, `test_sin_decisiones_las_metricas_de_decisiones_quedan_nulas`, `test_desde_y_hasta_acotan_postulaciones_y_decisiones`, `test_cifras_coherentes_con_los_datos_semilla` | **Verde** |
| RF-A-20 | HU-04 | Aislar los datos de cada empresa | Un usuario de A no ve ni modifica datos de B por ninguna pantalla ni endpoint | `test_aislamiento_multiempresa.py` (73 pruebas: 66 endpoints RRHH + 11 de candidato, cobertura automática); `test_rls.py` (capa de base de datos) | **Verde** |

## Verificación manual pendiente (no automatizable desde el backend)

Ninguna. RF-A-01 (redirección al dashboard) y RF-A-02 (renovación transparente de la
sesión) eran las dos únicas partes de un criterio que solo se podían verificar a mano, en
el navegador — por ser comportamiento del frontend (enrutamiento y temporización del
cliente), no una respuesta del backend. TST-A-03 (HU-25, DEC-020) las cubre con Playwright
contra el backend y el frontend reales: ver el detalle en las filas de RF-A-01 y RF-A-02.

**Resultado global:** 20/20 RF-A en verde, sin verificaciones manuales pendientes.

## Historial

| Fecha | Cambio |
|---|---|
| 2026-11-01 | Primer registro (TST-A-01): 20/20 RF-A en verde; se agregaron las pruebas automáticas que faltaban para RF-A-10, RF-A-12, RF-A-16 y RF-A-18 |
| 2026-11-01 | RF-A-12 reforzado en la base de datos: `decisiones_candidato` revoca `UPDATE`/`DELETE` a `vael_app` y `vael_system` (migración `c8d9e0f1a2b3`); ya no depende solo de la convención del código |
| 2026-11-01 | TST-A-03 (E2E con Playwright, DEC-020): RF-A-01 y RF-A-02 pasan de verificación manual a automática; sin verificaciones manuales pendientes |
