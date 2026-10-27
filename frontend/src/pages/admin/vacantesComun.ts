import type { Esquemas } from '../../api/cliente'
import type { BadgeVariant } from '../../components/ui/Badge'
import type { Opcion } from '../../components/ui/Formulario'

/** Tipos y etiquetas compartidos por las pantallas de vacantes (DEV-A-04). */

export type Vacante = Esquemas['VacanteResponse']
export type EstadoVacante = Vacante['estado']
export type Nivel = NonNullable<Vacante['nivel_experiencia']>
export type Modalidad = NonNullable<Vacante['modalidad']>
export type Contrato = NonNullable<Vacante['tipo_contrato']>
export type Prioridad = Vacante['prioridad']

export const ESTADOS: Record<EstadoVacante, { etiqueta: string; variante: BadgeVariant }> = {
  borrador: { etiqueta: 'Borrador', variante: 'neutral' },
  abierta: { etiqueta: 'Abierta', variante: 'success' },
  pausada: { etiqueta: 'Pausada', variante: 'warning' },
  cerrada: { etiqueta: 'Cerrada', variante: 'neutral' },
}

export const PRIORIDADES: Record<Prioridad, { etiqueta: string; variante: BadgeVariant }> = {
  urgente: { etiqueta: 'Urgente', variante: 'danger' },
  alta: { etiqueta: 'Alta', variante: 'warning' },
  media: { etiqueta: 'Media', variante: 'neutral' },
  baja: { etiqueta: 'Baja', variante: 'neutral' },
}

export const NIVELES: readonly Opcion<Nivel>[] = [
  { valor: 'practicante', etiqueta: 'Practicante' },
  { valor: 'junior', etiqueta: 'Junior' },
  { valor: 'semi_senior', etiqueta: 'Semi senior' },
  { valor: 'senior', etiqueta: 'Senior' },
  { valor: 'lider', etiqueta: 'Líder' },
]

export const MODALIDADES: readonly Opcion<Modalidad>[] = [
  { valor: 'presencial', etiqueta: 'Presencial' },
  { valor: 'remoto', etiqueta: 'Remoto' },
  { valor: 'hibrido', etiqueta: 'Híbrido' },
]

export const CONTRATOS: readonly Opcion<Contrato>[] = [
  { valor: 'indefinido', etiqueta: 'Indefinido' },
  { valor: 'plazo_fijo', etiqueta: 'Plazo fijo' },
  { valor: 'practicas', etiqueta: 'Prácticas' },
  { valor: 'freelance', etiqueta: 'Freelance' },
  { valor: 'part_time', etiqueta: 'Medio tiempo' },
]

export const OPCIONES_PRIORIDAD: readonly Opcion<Prioridad>[] = [
  { valor: 'baja', etiqueta: 'Baja' },
  { valor: 'media', etiqueta: 'Media' },
  { valor: 'alta', etiqueta: 'Alta' },
  { valor: 'urgente', etiqueta: 'Urgente' },
]

export function etiquetaDe<T extends string>(opciones: readonly Opcion<T>[], valor: T | null | undefined): string {
  return opciones.find((o) => o.valor === valor)?.etiqueta ?? ''
}
