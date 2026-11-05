import { useQuery } from '@tanstack/react-query'
import { api, datos, type Esquemas } from '../../api/cliente'
import type { BadgeVariant } from '../../components/ui/Badge'

/** Tipos y utilidades compartidas por las pantallas de evaluaciones (HU-19, DEV-A-07). */

export type Examen = Esquemas['ExamenResponse']
export type ExamenDetalle = Esquemas['ExamenDetalleResponse']
export type Entrevista = Esquemas['EntrevistaResponse']
export type EntrevistaDetalle = Esquemas['EntrevistaDetalleResponse']
export type EventoAuditoriaGeneral = Esquemas['EventoAuditoriaGeneralResponse']
export type Semaforo = Esquemas['ExamenResponse']['semaforo']
export type Severidad = Esquemas['EventoAuditoriaGeneralResponse']['severidad']

export const SEMAFORO: Record<Semaforo, { etiqueta: string; variante: BadgeVariant }> = {
  verde: { etiqueta: 'Verde', variante: 'success' },
  amarillo: { etiqueta: 'Amarillo', variante: 'warning' },
  rojo: { etiqueta: 'Rojo', variante: 'danger' },
}

export const SEVERIDAD: Record<Severidad, { etiqueta: string; variante: BadgeVariant }> = {
  alta: { etiqueta: 'Alta', variante: 'danger' },
  media: { etiqueta: 'Media', variante: 'warning' },
  baja: { etiqueta: 'Baja', variante: 'neutral' },
}

const ESTADO_EXAMEN_VARIANTE: Record<Examen['estado'], BadgeVariant> = {
  generando: 'neutral',
  pendiente: 'neutral',
  en_curso: 'info',
  finalizado: 'success',
  expirado: 'neutral',
}

const ESTADO_ENTREVISTA_VARIANTE: Record<Entrevista['estado'], BadgeVariant> = {
  pendiente: 'neutral',
  en_curso: 'info',
  finalizada: 'success',
  expirada: 'neutral',
}

export function varianteEstadoExamen(estado: Examen['estado']): BadgeVariant {
  return ESTADO_EXAMEN_VARIANTE[estado]
}

export function varianteEstadoEntrevista(estado: Entrevista['estado']): BadgeVariant {
  return ESTADO_ENTREVISTA_VARIANTE[estado]
}

/** Todos los candidatos del tenant, para cruzar nombre y vacante por id (sin endpoint dedicado). */
export function useCandidatos() {
  return useQuery({
    queryKey: ['candidatos', 'todos'],
    queryFn: async () => datos(await api.GET('/api/candidatos', { params: { query: {} } })),
  })
}

/** Todas las vacantes del tenant, para mostrar el título junto a cada examen o entrevista. */
export function useVacantes() {
  return useQuery({
    queryKey: ['vacantes', 'todas'],
    queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })),
  })
}

export function nombreCompleto(candidato: { nombre: string; apellidos: string } | undefined): string {
  return candidato ? `${candidato.nombre} ${candidato.apellidos}` : 'Candidato'
}
