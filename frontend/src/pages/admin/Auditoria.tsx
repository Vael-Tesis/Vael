import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { SEMAFORO, SEVERIDAD, nombreCompleto, useCandidatos, type EventoAuditoriaGeneral } from './evaluacionesComun'

/**
 * P-15 Auditoría (HU-19, RF-A-16): panel de integridad global, con los eventos de examen y de
 * entrevista juntos (doc 15, V-18). El semáforo acumulado solo existe en el examen (el modelo
 * de entrevista no lleva un puntaje de riesgo propio, según doc 08): las tarjetas de resumen
 * se calculan sobre los exámenes; el detalle de eventos abajo cubre ambas etapas.
 */

export default function Auditoria() {
  const navigate = useNavigate()
  const eventos = useQuery({
    queryKey: ['auditoria'],
    queryFn: async () => datos(await api.GET('/api/evaluaciones/auditoria', { params: { query: {} } }), 'No se pudo cargar la auditoría'),
  })
  const examenes = useQuery({
    queryKey: ['examenes', {}],
    queryFn: async () => datos(await api.GET('/api/evaluaciones/examenes', { params: { query: {} } })),
  })
  const candidatos = useCandidatos()

  const candidatoPorId = new Map((candidatos.data ?? []).map((c) => [c.id, c]))
  const examenPorCandidato = new Map((examenes.data ?? []).map((e) => [e.candidato_id, e]))

  const porCandidato = new Map<string, EventoAuditoriaGeneral[]>()
  for (const ev of eventos.data ?? []) {
    if (!ev.candidato_id) continue
    porCandidato.set(ev.candidato_id, [...(porCandidato.get(ev.candidato_id) ?? []), ev])
  }

  const examenesList = examenes.data ?? []
  const resumen = [
    { label: 'Sin incidencias', valor: examenesList.filter((e) => e.semaforo === 'verde').length, variante: 'success' as const },
    { label: 'Revisión opcional', valor: examenesList.filter((e) => e.semaforo === 'amarillo').length, variante: 'warning' as const },
    { label: 'Revisión obligatoria', valor: examenesList.filter((e) => e.semaforo === 'rojo').length, variante: 'danger' as const },
  ]

  const grupos = [...porCandidato.entries()].sort(([, a], [, b]) => b.length - a.length)

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader title="Auditoría" description="Panel de integridad de exámenes y entrevistas" />

      {eventos.isLoading || examenes.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : eventos.error ? (
        <Card><EmptyState title="No se pudo cargar la auditoría" description={mensajeDe(eventos.error, 'Intenta de nuevo')} /></Card>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
            {resumen.map((item, i) => (
              <motion.div key={item.label} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
                <Card>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{item.label}</p>
                  <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-1px', color: 'var(--text-primary)' }}>{item.valor}</p>
                  <Badge variant={item.variante}>exámenes</Badge>
                </Card>
              </motion.div>
            ))}
          </div>

          {grupos.length === 0 ? (
            <Card><EmptyState title="Sin eventos de auditoría" description="No se registró ningún evento de proctoring" /></Card>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {grupos.map(([candidatoId, eventosCandidato], i) => {
                const candidato = candidatoPorId.get(candidatoId)
                const examen = examenPorCandidato.get(candidatoId)
                return (
                  <motion.div key={candidatoId} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                    <Card>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
                        <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{nombreCompleto(candidato)}</p>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          {examen && (
                            <>
                              <Badge variant={SEMAFORO[examen.semaforo].variante}>● {SEMAFORO[examen.semaforo].etiqueta} — {examen.puntaje_riesgo} pts</Badge>
                              <button onClick={() => navigate(`/examenes/${examen.id}`)} style={{
                                background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 10px',
                                fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
                              }}>Ver examen</button>
                            </>
                          )}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {eventosCandidato.map((ev) => (
                          <div key={ev.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: 'var(--bg-page)', borderRadius: 6, fontSize: 12 }}>
                            <Badge variant={SEVERIDAD[ev.severidad].variante}>{SEVERIDAD[ev.severidad].etiqueta}</Badge>
                            <Badge variant="neutral">{ev.examen_id ? 'Examen' : 'Entrevista'}</Badge>
                            <span style={{ fontWeight: 500, color: 'var(--text-primary)', minWidth: 120 }}>{ev.tipo.replace(/_/g, ' ')}</span>
                            <span style={{ color: 'var(--text-muted)', flex: 1 }}>{ev.detalle}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                              {new Date(ev.timestamp).toLocaleString('es-PE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        ))}
                      </div>
                    </Card>
                  </motion.div>
                )
              })}
            </div>
          )}
        </>
      )}
    </div>
  )
}
