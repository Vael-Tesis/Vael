import type { Esquemas } from '../../api/cliente'
import type { BadgeVariant } from '../../components/ui/Badge'

/** Tipos y etiquetas compartidos por las pantallas de candidatos. */

export type Candidato = Esquemas['CandidatoResponse']
export type EstadoCandidato = Candidato['estado']
export type Clasificacion = NonNullable<Candidato['clasificacion_ia']>

export const ESTADOS_CANDIDATO: Record<EstadoCandidato, { etiqueta: string; variante: BadgeVariant }> = {
  postulado: { etiqueta: 'Postulado', variante: 'neutral' },
  cv_analizando: { etiqueta: 'Analizando CV', variante: 'info' },
  cv_por_confirmar: { etiqueta: 'CV por confirmar', variante: 'warning' },
  cv_aprobado: { etiqueta: 'CV aprobado', variante: 'success' },
  cv_rechazado: { etiqueta: 'Descartado en CV', variante: 'danger' },
  examen_pendiente: { etiqueta: 'Examen pendiente', variante: 'info' },
  examen_rendido: { etiqueta: 'Examen rendido', variante: 'info' },
  examen_por_confirmar: { etiqueta: 'Examen por confirmar', variante: 'warning' },
  examen_aprobado: { etiqueta: 'Examen aprobado', variante: 'success' },
  examen_rechazado: { etiqueta: 'Descartado en examen', variante: 'danger' },
  entrevista_pendiente: { etiqueta: 'Entrevista pendiente', variante: 'info' },
  entrevista_realizada: { etiqueta: 'Entrevista realizada', variante: 'warning' },
  finalista: { etiqueta: 'Finalista', variante: 'success' },
  contratado: { etiqueta: 'Contratado', variante: 'success' },
  descartado: { etiqueta: 'Descartado', variante: 'danger' },
}

export const CLASIFICACIONES: Record<Clasificacion, { etiqueta: string; variante: BadgeVariant }> = {
  altamente_recomendado: { etiqueta: 'Altamente recomendado', variante: 'success' },
  recomendado: { etiqueta: 'Recomendado', variante: 'info' },
  requiere_revision: { etiqueta: 'Requiere revisión', variante: 'warning' },
  no_apto: { etiqueta: 'No apto', variante: 'danger' },
}

/** DEC-024: los cinco criterios ponderados del desglose de score_cv, en el mismo orden del prompt. */
export const CRITERIOS_SCORE_CV: readonly { clave: string; etiqueta: string; maximo: number }[] = [
  { clave: 'match_habilidades', etiqueta: 'Match de habilidades', maximo: 40 },
  { clave: 'experiencia', etiqueta: 'Experiencia', maximo: 20 },
  { clave: 'formacion', etiqueta: 'Formación', maximo: 15 },
  { clave: 'coherencia', etiqueta: 'Coherencia', maximo: 15 },
  { clave: 'trayectoria', etiqueta: 'Trayectoria', maximo: 10 },
]
