import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'

const DEMO = [
  { id: '1', candidato: { nombre: 'Ana', apellidos: 'Flores' }, semaforo: 'rojo', puntaje_riesgo: 24, eventos: [
    { tipo: 'devtools', severidad: 'alta', detalle: 'DevTools abierto', timestamp: '2026-09-19T15:12:00Z' },
    { tipo: 'copy_paste', severidad: 'alta', detalle: 'Pegado detectado', timestamp: '2026-09-19T15:18:00Z' },
    { tipo: 'perdida_foco', severidad: 'media', detalle: 'Cambio de pestaña', timestamp: '2026-09-19T15:22:00Z' },
  ]},
  { id: '2', candidato: { nombre: 'Carlos', apellidos: 'Pérez' }, semaforo: 'amarillo', puntaje_riesgo: 10, eventos: [
    { tipo: 'cambio_ventana', severidad: 'media', detalle: 'Cambio de ventana x2', timestamp: '2026-09-21T10:05:00Z' },
    { tipo: 'inactividad', severidad: 'baja', detalle: 'Inactivo +2 min', timestamp: '2026-09-21T10:30:00Z' },
  ]},
]

const SEMAFORO_CONFIG = {
  verde:    { color: 'var(--success-text)', bg: 'var(--success-bg)', label: 'Verde ≤ 6 pts' },
  amarillo: { color: 'var(--warning-text)', bg: 'var(--warning-bg)', label: 'Amarillo 7-18 pts' },
  rojo:     { color: 'var(--danger-text)',  bg: 'var(--danger-bg)',  label: 'Rojo > 18 pts' },
}

const SEVERIDAD_COLOR = {
  alta:  'var(--danger-text)',
  media: 'var(--warning-text)',
  baja:  'var(--text-muted)',
}

function SemaforoTag({ valor, puntaje }) {
  const s = SEMAFORO_CONFIG[valor] || SEMAFORO_CONFIG.verde
  return (
    <span style={{
      background: s.bg, color: s.color,
      fontSize: 12, fontWeight: 500, borderRadius: 6,
      padding: '4px 10px', display: 'inline-flex', gap: 6,
    }}>
      ● {s.label} — {puntaje} pts acumulados
    </span>
  )
}

export default function Auditoria() {
  const { data } = useQuery({
    queryKey: ['auditoria'],
    queryFn: () => api.get('/evaluaciones/auditoria').then(r => r.data).catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const registros = data || DEMO
  const criticos = registros.filter(r => r.semaforo === 'rojo')
  const revision = registros.filter(r => r.semaforo === 'amarillo')

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Auditoría"
        description="Panel de integridad de los exámenes realizados"
      />

      {/* Resumen */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Sin incidencias', valor: registros.filter(r => r.semaforo === 'verde').length, color: 'var(--success-text)', bg: 'var(--success-bg)' },
          { label: 'Revisión opcional', valor: revision.length, color: 'var(--warning-text)', bg: 'var(--warning-bg)' },
          { label: 'Revisión obligatoria', valor: criticos.length, color: 'var(--danger-text)', bg: 'var(--danger-bg)' },
        ].map((item, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            style={{
              background: item.bg, border: `1px solid ${item.bg}`,
              borderRadius: 8, padding: '14px 16px',
            }}
          >
            <p style={{ fontSize: 11, color: item.color, marginBottom: 6 }}>{item.label}</p>
            <p style={{ fontSize: 28, fontWeight: 600, color: item.color, letterSpacing: '-1px' }}>
              {item.valor}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Registros con eventos */}
      {registros.filter(r => r.semaforo !== 'verde').length === 0 ? (
        <Card><EmptyState title="Sin incidencias" description="Todos los exámenes tienen semáforo verde" /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {registros.filter(r => r.semaforo !== 'verde').map((r, i) => (
            <motion.div key={r.id}
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                      {r.candidato?.nombre} {r.candidato?.apellidos}
                    </p>
                  </div>
                  <SemaforoTag valor={r.semaforo} puntaje={r.puntaje_riesgo} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {(r.eventos || []).map((ev, j) => (
                    <div key={j} style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '8px 10px',
                      background: 'var(--bg-page)', borderRadius: 6,
                      fontSize: 12,
                    }}>
                      <span style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: SEVERIDAD_COLOR[ev.severidad],
                        flexShrink: 0,
                      }} />
                      <span style={{ fontWeight: 500, color: 'var(--text-primary)', minWidth: 120 }}>
                        {ev.tipo.replace(/_/g, ' ')}
                      </span>
                      <span style={{ color: 'var(--text-muted)', flex: 1 }}>{ev.detalle}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                        {new Date(ev.timestamp).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}