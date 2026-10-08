import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import { useNavigate } from 'react-router-dom'

const DEMO = [
  { id: '1', candidato: { nombre: 'Jorge', apellidos: 'Torres' }, vacante: { titulo: 'DevOps Engineer' }, nota: 16.8, estado: 'finalizada', duracion_minutos: 22, dimensiones_json: { claridad_expresion: 17, coherencia_respuestas: 16, precision_tecnica: 18, comunicacion_efectiva: 16, seguridad_confianza: 15 } },
  { id: '2', candidato: { nombre: 'María', apellidos: 'Alvarado' }, vacante: { titulo: 'Full Stack Developer' }, nota: 15.2, estado: 'finalizada', duracion_minutos: 19, dimensiones_json: { claridad_expresion: 15, coherencia_respuestas: 16, precision_tecnica: 14, comunicacion_efectiva: 16, seguridad_confianza: 15 } },
  { id: '3', candidato: { nombre: 'Lucía', apellidos: 'Ramírez' }, vacante: { titulo: 'UX Designer' }, nota: null, estado: 'pendiente', duracion_minutos: null, dimensiones_json: null },
]

const ESTADO_VARIANT = {
  finalizada: 'success',
  en_curso:   'info',
  pendiente:  'neutral',
  expirada:   'neutral',
}

const DIMENSIONES_LABEL = {
  claridad_expresion:   'Claridad',
  coherencia_respuestas:'Coherencia',
  precision_tecnica:    'Precisión',
  comunicacion_efectiva:'Comunicación',
  seguridad_confianza:  'Seguridad',
}

function MiniBar({ valor, max = 20 }) {
  const pct = Math.round(((valor || 0) / max) * 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 3, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--text-primary)', borderRadius: 999 }} />
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-secondary)', minWidth: 20 }}>{valor}</span>
    </div>
  )
}

export default function EntrevistasIA() {
  const { data } = useQuery({
    queryKey: ['entrevistas'],
    queryFn: () => api.get('/entrevista/lista').then(r => r.data).catch(() => DEMO),
  })

  const entrevistas = data || DEMO
  const navigate = useNavigate()
  
  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Entrevistas IA"
        description="Resultados de entrevistas conducidas por EVA"
      />

      {entrevistas.length === 0 ? (
        <Card><EmptyState title="Sin entrevistas" /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {entrevistas.map((e, i) => {
            const dims = e.dimensiones_json || null
            return (
              <motion.div key={e.id}
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <Card>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                          {e.candidato?.nombre} {e.candidato?.apellidos}
                        </p>
                        <Badge variant={ESTADO_VARIANT[e.estado] || 'neutral'}>{e.estado}</Badge>
                      </div>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                        {e.vacante?.titulo}
                        {e.duracion_minutos && ` · ${e.duracion_minutos} min`}
                      </p>
                      {dims && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
                          {Object.entries(dims).map(([key, val]) => (
                            <div key={key}>
                              <p style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
                                {DIMENSIONES_LABEL[key] || key}
                              </p>
                              <MiniBar valor={val} />
                            </div>
                          ))}
                        </div>
                      )}

                      {/* ← AQUÍ el botón nuevo */}
                      <button onClick={() => navigate(`/entrevistas/${e.id}`)} style={{
                        marginTop: 10, background: 'none', border: '1px solid var(--border)',
                        borderRadius: 6, padding: '5px 12px', fontSize: 12,
                        color: 'var(--text-secondary)', cursor: 'pointer',
                      }}>Ver detalle completo</button>

                    </div>
                    <div style={{ textAlign: 'center', flexShrink: 0 }}>
                      <p style={{
                        fontSize: 28, fontWeight: 600, letterSpacing: '-1px',
                        color: e.nota >= 13 ? 'var(--success-text)' : e.nota != null ? 'var(--danger-text)' : 'var(--text-muted)',
                      }}>
                        {e.nota != null ? e.nota.toFixed(1) : '—'}
                      </p>
                      <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>/ 20</p>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}