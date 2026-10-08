import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'

const DEMO = [
  { id: '1', nombre: 'Jorge', apellidos: 'Torres',   score_cv: 92, score_final: 18.4, nota_examen: 17, nota_entrevista: 16.8, estado: 'finalista' },
  { id: '2', nombre: 'María', apellidos: 'Alvarado', score_cv: 87, score_final: 16.9, nota_examen: 16, nota_entrevista: 15.2, estado: 'entrevista_realizada' },
  { id: '3', nombre: 'Carlos', apellidos: 'Pérez',   score_cv: 74, score_final: 14.1, nota_examen: 14, nota_entrevista: 13.5, estado: 'entrevista_realizada' },
  { id: '4', nombre: 'Lucía', apellidos: 'Ramírez',  score_cv: 61, score_final: 12.3, nota_examen: 13, nota_entrevista: null, estado: 'examen_aprobado' },
]

function ScoreBar({ value, max = 20, color = 'var(--text-primary)' }) {
  const pct = Math.round(((value || 0) / max) * 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ height: '100%', background: color, borderRadius: 999 }}
        />
      </div>
      <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', minWidth: 28 }}>
        {value != null ? value.toFixed(1) : '—'}
      </span>
    </div>
  )
}

export default function Ranking() {
  const { data } = useQuery({
    queryKey: ['ranking'],
    queryFn: () => api.get('/candidatos/ranking').then(r => r.data).catch(() => DEMO),
  })

  const ranking = (data || DEMO).sort((a, b) => (b.score_final || 0) - (a.score_final || 0))

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Ranking"
        description="Candidatos ordenados por score final ponderado"
      />

      <Card padding="0">
        {/* Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '36px 1fr 120px 120px 120px 100px',
          padding: '8px 16px',
          borderBottom: '1px solid var(--border)',
          fontSize: 11, fontWeight: 500,
          color: 'var(--text-muted)', textTransform: 'uppercase',
          letterSpacing: '0.05em', gap: 12,
        }}>
          <span>#</span>
          <span>Candidato</span>
          <span>Score CV (25%)</span>
          <span>Examen (40%)</span>
          <span>Entrevista (35%)</span>
          <span style={{ textAlign: 'center' }}>Score final</span>
        </div>

        {ranking.length === 0 ? (
          <EmptyState title="Sin datos" description="Selecciona una vacante para ver el ranking" />
        ) : (
          ranking.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                display: 'grid',
                gridTemplateColumns: '36px 1fr 120px 120px 120px 100px',
                padding: '12px 16px',
                borderBottom: '1px solid var(--border)',
                alignItems: 'center', gap: 12,
              }}
            >
              <span style={{
                fontSize: 13, fontWeight: 600,
                color: i === 0 ? 'var(--warning-text)' : i === 1 ? 'var(--text-secondary)' : 'var(--text-muted)',
              }}>
                {i + 1}
              </span>
              <div>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                  {c.nombre} {c.apellidos}
                </p>
              </div>
              <ScoreBar value={c.score_cv != null ? c.score_cv / 5 : null} max={20} />
              <ScoreBar value={c.nota_examen} max={20} />
              <ScoreBar value={c.nota_entrevista} max={20} />
              <div style={{ textAlign: 'center' }}>
                <span style={{
                  fontSize: 15, fontWeight: 600,
                  color: i === 0 ? 'var(--success-text)' : 'var(--text-primary)',
                }}>
                  {c.score_final != null ? c.score_final.toFixed(1) : '—'}
                </span>
              </div>
            </motion.div>
          ))
        )}
      </Card>
    </div>
  )
}