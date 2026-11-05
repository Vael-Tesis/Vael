import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import Spinner from '../../components/ui/Spinner'
import { Volver } from '../../components/ui/Formulario'
import { SEMAFORO, SEVERIDAD, nombreCompleto, useCandidatos, useVacantes } from './evaluacionesComun'

/** P-12 Detalle de examen (HU-19, RF-A-16): preguntas calificadas y auditoría en la misma vista. */

function PuntosBadge({ obtenidos, max }: { obtenidos: number | null; max: number }) {
  const color = obtenidos === max ? 'var(--success-text)' : obtenidos === 0 ? 'var(--danger-text)' : 'var(--warning-text)'
  const bg = obtenidos === max ? 'var(--success-bg)' : obtenidos === 0 ? 'var(--danger-bg)' : 'var(--warning-bg)'
  return (
    <span style={{ background: bg, color, fontSize: 12, fontWeight: 600, borderRadius: 6, padding: '3px 10px', flexShrink: 0 }}>
      {obtenidos ?? 0}/{max} pts
    </span>
  )
}

export default function ExamenDetalle() {
  const { id = '' } = useParams()
  const navigate = useNavigate()

  const examen = useQuery({
    queryKey: ['examen', id],
    queryFn: async () => datos(await api.GET('/api/evaluaciones/examenes/{examen_id}', { params: { path: { examen_id: id } } }), 'No se pudo cargar el examen'),
  })
  const auditoria = useQuery({
    queryKey: ['examen', id, 'auditoria'],
    queryFn: async () => datos(await api.GET('/api/evaluaciones/examenes/{examen_id}/auditoria', { params: { path: { examen_id: id } } })),
  })
  const candidatos = useCandidatos()
  const vacantes = useVacantes()

  if (examen.isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
  if (examen.error || !examen.data) {
    return <Card><EmptyState title="No se pudo cargar el examen" description={mensajeDe(examen.error, 'Intenta de nuevo')} /></Card>
  }

  const e = examen.data
  const candidato = (candidatos.data ?? []).find((c) => c.id === e.candidato_id)
  const vacante = (vacantes.data ?? []).find((v) => v.id === e.vacante_id)
  const eventos = auditoria.data ?? []
  const semaforo = SEMAFORO[e.semaforo]

  return (
    <div style={{ padding: '20px 24px', maxWidth: 820 }}>
      <Volver onClick={() => navigate('/examenes')}>Volver a exámenes</Volver>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{nombreCompleto(candidato)}</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            {vacante?.titulo ?? 'Vacante'} · {e.duracion_minutos} min
            {e.fecha_fin && ` · ${new Date(e.fecha_fin).toLocaleDateString('es-PE')}`}
          </p>
        </div>
        <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-1px', color: e.nota != null && e.nota >= 13 ? 'var(--success-text)' : 'var(--danger-text)' }}>
          {e.nota != null ? `${e.nota}/20` : '—'}
        </p>
      </div>

      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: eventos.length ? 12 : 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Badge variant={semaforo.variante}>● {semaforo.etiqueta} — {e.puntaje_riesgo} pts de riesgo</Badge>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {eventos.length} evento{eventos.length !== 1 ? 's' : ''} de auditoría
            </span>
          </div>
        </div>
        {eventos.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {eventos.map((ev) => (
              <div key={ev.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: 'var(--bg-page)', borderRadius: 6, fontSize: 12 }}>
                <Badge variant={SEVERIDAD[ev.severidad].variante}>{SEVERIDAD[ev.severidad].etiqueta}</Badge>
                <span style={{ fontWeight: 500, color: 'var(--text-primary)', minWidth: 120 }}>{ev.tipo.replace(/_/g, ' ')}</span>
                <span style={{ color: 'var(--text-muted)', flex: 1 }}>{ev.detalle}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                  {new Date(ev.timestamp).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {e.preguntas.length === 0 ? (
          <Card><EmptyState title="Sin preguntas" /></Card>
        ) : (
          e.preguntas.map((p, i) => (
            <motion.div key={p.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      Pregunta {p.orden} · {p.tipo === 'multiple_choice' ? 'Opción múltiple' : 'Abierta'}
                    </p>
                    <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.4 }}>{p.enunciado}</p>
                  </div>
                  <PuntosBadge obtenidos={p.puntos_obtenidos} max={p.puntos_max} />
                </div>

                {p.tipo === 'multiple_choice' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {(p.opciones_json ?? []).map((op) => {
                      const esCorrecta = op === p.respuesta_correcta
                      const esElegida = op === p.respuesta_candidato
                      return (
                        <div key={op} style={{
                          padding: '8px 12px', borderRadius: 6, fontSize: 13,
                          background: esCorrecta ? 'var(--success-bg)' : esElegida ? 'var(--danger-bg)' : 'var(--bg-page)',
                          color: esCorrecta ? 'var(--success-text)' : esElegida ? 'var(--danger-text)' : 'var(--text-secondary)',
                          display: 'flex', justifyContent: 'space-between',
                        }}>
                          <span>{op}</span>
                          {esCorrecta && <span>✓ Correcta</span>}
                          {esElegida && !esCorrecta && <span>✗ Elegida</span>}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <>
                    <div style={{ padding: 12, background: 'var(--bg-page)', borderRadius: 6, fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: p.feedback_ia ? 10 : 0 }}>
                      {p.respuesta_candidato || '—'}
                    </div>
                    {p.feedback_ia && (
                      <div style={{ padding: '8px 12px', borderRadius: 6, background: 'var(--info-bg)', color: 'var(--info-text)', fontSize: 12, lineHeight: 1.5 }}>
                        <strong>Feedback IA:</strong> {p.feedback_ia}
                      </div>
                    )}
                  </>
                )}
              </Card>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
