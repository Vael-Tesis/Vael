import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import Spinner from '../../components/ui/Spinner.jsx'
import { useNavigate } from 'react-router-dom'

const DEMO = [
  { id: '1', candidato: { nombre: 'María', apellidos: 'Alvarado' }, vacante: { titulo: 'Full Stack Developer' }, nota: 16.5, estado: 'finalizado', semaforo: 'verde', puntaje_riesgo: 2, fecha_fin: '2026-09-20T14:30:00Z' },
  { id: '2', candidato: { nombre: 'Carlos', apellidos: 'Pérez' }, vacante: { titulo: 'Full Stack Developer' }, nota: 14.0, estado: 'finalizado', semaforo: 'amarillo', puntaje_riesgo: 10, fecha_fin: '2026-09-21T10:15:00Z' },
  { id: '3', candidato: { nombre: 'Lucía', apellidos: 'Ramírez' }, vacante: { titulo: 'UX Designer' }, nota: null, estado: 'en_curso', semaforo: 'verde', puntaje_riesgo: 0, fecha_fin: null },
  { id: '4', candidato: { nombre: 'Ana', apellidos: 'Flores' }, vacante: { titulo: 'Sales Executive' }, nota: 9.5, estado: 'finalizado', semaforo: 'rojo', puntaje_riesgo: 24, fecha_fin: '2026-09-19T16:00:00Z' },
]

const SEMAFORO = {
  verde:    { bg: 'var(--success-bg)', color: 'var(--success-text)', label: 'Verde' },
  amarillo: { bg: 'var(--warning-bg)', color: 'var(--warning-text)', label: 'Amarillo' },
  rojo:     { bg: 'var(--danger-bg)',  color: 'var(--danger-text)',  label: 'Rojo' },
}

const ESTADO_VARIANT = {
  finalizado: 'success',
  en_curso:   'info',
  pendiente:  'neutral',
  expirado:   'neutral',
}

function Semaforo({ valor }) {
  const s = SEMAFORO[valor] || SEMAFORO.verde
  return (
    <span style={{
      background: s.bg, color: s.color,
      fontSize: 11, fontWeight: 500,
      borderRadius: 4, padding: '2px 7px',
    }}>
      ● {s.label}
    </span>
  )
}

export default function Examenes() {
  const [filtro, setFiltro] = useState('todos')
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['examenes'],
    queryFn: () => api.get('/evaluaciones/examenes').then(r => r.data).catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const examenes = data || DEMO
  const filtrados = filtro === 'todos' ? examenes
    : examenes.filter(e => e.semaforo === filtro)

  const FILTROS = [
    { key: 'todos', label: 'Todos' },
    { key: 'verde', label: '● Verde' },
    { key: 'amarillo', label: '● Amarillo' },
    { key: 'rojo', label: '● Rojo' },
  ]

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Exámenes"
        description="Resultados y estado de integridad de cada evaluación"
      />

      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {FILTROS.map(f => (
          <button key={f.key} onClick={() => setFiltro(f.key)} style={{
            padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
            cursor: 'pointer', border: '1px solid var(--border)',
            background: filtro === f.key ? 'var(--text-primary)' : 'var(--bg-card)',
            color: filtro === f.key ? 'var(--bg-card)' : 'var(--text-secondary)',
            transition: 'all 150ms ease',
          }}>{f.label}</button>
        ))}
      </div>

      <Card padding="0">
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 160px 80px 100px 110px 70px',
          padding: '8px 16px',
          borderBottom: '1px solid var(--border)',
          fontSize: 11, fontWeight: 500,
          color: 'var(--text-muted)', textTransform: 'uppercase',
          letterSpacing: '0.05em', gap: 12,
        }}>
          <span>Candidato</span>
          <span>Vacante</span>
          <span style={{ textAlign: 'center' }}>Nota</span>
          <span>Integridad</span>
          <span>Estado</span>
          <span></span>
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
        ) : filtrados.length === 0 ? (
          <EmptyState title="Sin exámenes" />
        ) : filtrados.map((e, i) => (
          <motion.div key={e.id}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            transition={{ delay: i * 0.04 }}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 160px 80px 100px 110px 70px',
              padding: '11px 16px',
              borderBottom: '1px solid var(--border)',
              alignItems: 'center', gap: 12,
            }}
          >
            <div>
              <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                {e.candidato?.nombre} {e.candidato?.apellidos}
              </p>
              <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Riesgo: {e.puntaje_riesgo} pts
              </p>
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {e.vacante?.titulo}
            </span>
            <div style={{ textAlign: 'center' }}>
              <span style={{
                fontSize: 14, fontWeight: 600,
                color: e.nota >= 13 ? 'var(--success-text)' : e.nota != null ? 'var(--danger-text)' : 'var(--text-muted)',
              }}>
                {e.nota != null ? `${e.nota}/20` : '—'}
              </span>
            </div>
            <Semaforo valor={e.semaforo} />
            <Badge variant={ESTADO_VARIANT[e.estado] || 'neutral'}>{e.estado}</Badge>
            <button onClick={() => navigate(`/examenes/${e.id}`)} style={{
              background: 'none', border: '1px solid var(--border)',
              borderRadius: 6, padding: '4px 10px',
              fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
            }}>Ver</button>
          </motion.div>
        ))}
      </Card>
    </div>
  )
}