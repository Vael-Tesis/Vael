import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import { AreaTexto } from '../../components/ui/Formulario'

/**
 * Decisión humana sobre la recomendación de la IA (DEC-009, HU-15). Confirmar la
 * recomendación no exige justificación; decidir lo contrario sí. Abrir el panel registra
 * `revision_inicio`, con el que se miden los minutos de revisión (OE1).
 */

export type Etapa = Esquemas['DecisionRequest']['etapa']
export type Sentido = Esquemas['DecisionRequest']['decision']

export interface Recomendacion {
  recomendacion_ia: Sentido | null
  puntaje: number | null
  umbral: number | null
  justificacion_ia: string | null
  semaforo?: Esquemas['RecomendacionPendienteResponse']['semaforo']
}

export const ETAPAS: Record<Etapa, string> = { cv: 'CV', examen: 'Examen', entrevista: 'Entrevista' }

const ACCION: Record<Etapa, Record<Sentido, string>> = {
  cv: { avanzar: 'Avanzar al examen', descartar: 'Descartar' },
  examen: { avanzar: 'Invitar a la entrevista', descartar: 'Descartar' },
  entrevista: { avanzar: 'Marcar como finalista', descartar: 'Descartar' },
}

const ESCALA: Record<Etapa, string> = { cv: '/100', examen: '/20', entrevista: '/20' }

const SEMAFORO: Record<'verde' | 'amarillo' | 'rojo', { etiqueta: string; variante: 'success' | 'warning' | 'danger' }> = {
  verde: { etiqueta: 'Integridad: verde', variante: 'success' },
  amarillo: { etiqueta: 'Integridad: amarillo', variante: 'warning' },
  rojo: { etiqueta: 'Integridad: rojo', variante: 'danger' },
}

export function AvisoSupervision() {
  return (
    <p style={{ fontSize: 12, color: 'var(--brand)', background: 'var(--brand-soft)', padding: '6px 10px', borderRadius: 6, display: 'inline-block' }}>
      La IA recomienda; la decisión es tuya.
    </p>
  )
}

export function ResumenRecomendacion({ etapa, recomendacion }: { etapa: Etapa; recomendacion: Recomendacion }) {
  const { recomendacion_ia, puntaje, umbral, semaforo } = recomendacion
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
      {recomendacion_ia ? (
        <Badge variant={recomendacion_ia === 'avanzar' ? 'success' : 'danger'}>
          IA recomienda {recomendacion_ia === 'avanzar' ? 'avanzar' : 'descartar'}
        </Badge>
      ) : (
        <Badge variant="neutral">Sin recomendación de la IA</Badge>
      )}
      {puntaje !== null && (
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Puntaje {puntaje}{ESCALA[etapa]}{umbral !== null && ` · umbral ${umbral}`}
        </span>
      )}
      {semaforo && <Badge variant={SEMAFORO[semaforo].variante}>{SEMAFORO[semaforo].etiqueta}</Badge>}
    </div>
  )
}

export default function PanelDecision({
  candidatoId, etapa, recomendacion, onDecidido,
}: {
  candidatoId: string
  etapa: Etapa
  recomendacion: Recomendacion
  onDecidido?: () => void
}) {
  const queryClient = useQueryClient()
  const [revisionInicio] = useState(() => new Date().toISOString())
  const [contraria, setContraria] = useState<Sentido | null>(null)
  const [justificacion, setJustificacion] = useState('')

  const sugerida = recomendacion.recomendacion_ia
  const opuesta: Sentido | null = sugerida === 'avanzar' ? 'descartar' : sugerida === 'descartar' ? 'avanzar' : null

  const decidir = useMutation({
    mutationFn: async (decision: Sentido) =>
      datos(
        await api.POST('/api/candidatos/{candidato_id}/decision', {
          params: { path: { candidato_id: candidatoId } },
          body: { etapa, decision, justificacion_humana: justificacion.trim() || null, revision_inicio: revisionInicio },
        }),
        'No se pudo registrar la decisión',
      ),
    onSuccess: (fila) => {
      toast.success(fila.decision === 'avanzar' ? 'Decisión registrada: el candidato avanza' : 'Decisión registrada: se envió el correo de cierre')
      setContraria(null)
      setJustificacion('')
      queryClient.invalidateQueries({ queryKey: ['candidato', candidatoId] })
      queryClient.invalidateQueries({ queryKey: ['candidatos'] })
      queryClient.invalidateQueries({ queryKey: ['bandeja'] })
      onDecidido?.()
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo registrar la decisión')),
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <ResumenRecomendacion etapa={etapa} recomendacion={recomendacion} />
      {recomendacion.justificacion_ia && (
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{recomendacion.justificacion_ia}</p>
      )}

      {contraria === null ? (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {sugerida ? (
            <>
              <Button onClick={() => decidir.mutate(sugerida)} disabled={decidir.isPending}>
                Confirmar: {ACCION[etapa][sugerida].toLowerCase()}
              </Button>
              {opuesta && (
                <Button variant="secondary" onClick={() => setContraria(opuesta)} disabled={decidir.isPending}>
                  Decidir lo contrario
                </Button>
              )}
            </>
          ) : (
            (['avanzar', 'descartar'] as const).map((sentido) => (
              <Button key={sentido} variant={sentido === 'avanzar' ? 'primary' : 'secondary'} onClick={() => decidir.mutate(sentido)} disabled={decidir.isPending}>
                {ACCION[etapa][sentido]}
              </Button>
            ))
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label htmlFor={`justificacion-${candidatoId}`} style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>
            Justificación ({ACCION[etapa][contraria].toLowerCase()} en contra de la recomendación de la IA; obligatoria)
          </label>
          <AreaTexto id={`justificacion-${candidatoId}`} valor={justificacion} onChange={(e) => setJustificacion(e.target.value)}
            placeholder="Explica el criterio que aplicaste" />
          <div style={{ display: 'flex', gap: 8 }}>
            <Button variant={contraria === 'descartar' ? 'danger' : 'primary'} onClick={() => decidir.mutate(contraria)}
              disabled={decidir.isPending || justificacion.trim() === ''}>
              {ACCION[etapa][contraria]}
            </Button>
            <Button variant="ghost" onClick={() => { setContraria(null); setJustificacion('') }}>Cancelar</Button>
          </div>
        </div>
      )}
      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
        Avanzar envía al candidato el correo de la etapa siguiente; descartar envía un único correo de cierre, sin puntajes ni razones.
      </p>
    </div>
  )
}
