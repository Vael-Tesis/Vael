import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Button from '../../components/ui/Button.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Card from '../../components/ui/Card.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import Spinner from '../../components/ui/Spinner.jsx'

const ESTADO_CONFIG = {
  postulado:             { label: 'Postulado',        variant: 'neutral' },
  cv_analizando:         { label: 'Analizando CV',    variant: 'info' },
  cv_aprobado:           { label: 'CV aprobado',      variant: 'success' },
  cv_rechazado:          { label: 'CV rechazado',     variant: 'danger' },
  examen_pendiente:      { label: 'Examen pend.',     variant: 'warning' },
  examen_rendido:        { label: 'Examen rendido',   variant: 'info' },
  examen_aprobado:       { label: 'Examen aprobado',  variant: 'success' },
  examen_rechazado:      { label: 'Examen rechazado', variant: 'danger' },
  entrevista_pendiente:  { label: 'Entrevista pend.', variant: 'warning' },
  entrevista_realizada:  { label: 'Entrevistado',     variant: 'info' },
  finalista:             { label: 'Finalista',        variant: 'success' },
  contratado:            { label: 'Contratado',       variant: 'success' },
  descartado:            { label: 'Descartado',       variant: 'neutral' },
}

const DEMO = [
  { id: '1', nombre: 'María', apellidos: 'Alvarado', email: 'maria@gmail.com', score_cv: 87, estado: 'entrevista_pendiente', vacante: { titulo: 'Full Stack Developer' }, clasificacion_ia: 'altamente_recomendado' },
  { id: '2', nombre: 'Carlos', apellidos: 'Pérez', email: 'carlos@gmail.com', score_cv: 74, estado: 'cv_aprobado', vacante: { titulo: 'Full Stack Developer' }, clasificacion_ia: 'recomendado' },
  { id: '3', nombre: 'Lucía', apellidos: 'Ramírez', email: 'lucia@gmail.com', score_cv: 61, estado: 'examen_pendiente', vacante: { titulo: 'UX Designer' }, clasificacion_ia: 'recomendado' },
  { id: '4', nombre: 'Jorge', apellidos: 'Torres', email: 'jorge@gmail.com', score_cv: 92, estado: 'finalista', vacante: { titulo: 'DevOps Engineer' }, clasificacion_ia: 'altamente_recomendado' },
  { id: '5', nombre: 'Ana', apellidos: 'Flores', email: 'ana@gmail.com', score_cv: 45, estado: 'cv_rechazado', vacante: { titulo: 'Sales Executive' }, clasificacion_ia: 'no_apto' },
]

function ScoreBadge({ score }) {
  if (score == null) return <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>—</span>
  const variant = score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger'
  const COLORS = { success: { bg: 'var(--success-bg)', color: 'var(--success-text)' }, warning: { bg: 'var(--warning-bg)', color: 'var(--warning-text)' }, danger: { bg: 'var(--danger-bg)', color: 'var(--danger-text)' } }
  const c = COLORS[variant]
  return <span style={{ background: c.bg, color: c.color, fontSize: 11, fontWeight: 600, borderRadius: 4, padding: '2px 7px' }}>{score}</span>
}

function Initials({ nombre, apellidos }) {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: '50%',
      background: 'var(--bg-page)', border: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', flexShrink: 0,
    }}>
      {(nombre?.[0] || '') + (apellidos?.[0] || '')}
    </div>
  )
}

export default function Candidatos() {
  const [busqueda, setBusqueda] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['candidatos'],
    queryFn: () => api.get('/candidatos').then(r => r.data).catch(() => DEMO),
  })

  const candidatos = data || DEMO
  const navigate = useNavigate()
  const filtrados = candidatos.filter(c =>
    `${c.nombre} ${c.apellidos} ${c.email}`.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Candidatos"
        description="Lista de todos los postulantes"
        action={<Button onClick={() => navigate('/candidatos/registrar')}>+ Agregar candidato</Button>}
      />

      {/* Búsqueda */}
      <div style={{ marginBottom: 16 }}>
        <input
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre o email..."
          style={{
            height: 36, padding: '0 12px', width: 280,
            border: '1px solid var(--border)', borderRadius: 6,
            background: 'var(--bg-card)', color: 'var(--text-primary)',
            fontSize: 13, outline: 'none',
          }}
        />
      </div>

      {/* Tabla */}
      <Card padding="0">
        {/* Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 140px 90px 140px 80px',
          padding: '8px 16px',
          borderBottom: '1px solid var(--border)',
          fontSize: 11, fontWeight: 500,
          color: 'var(--text-muted)', textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          <span>Candidato</span>
          <span>Vacante</span>
          <span style={{ textAlign: 'center' }}>Score CV</span>
          <span>Estado</span>
          <span></span>
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
        ) : filtrados.length === 0 ? (
          <EmptyState title="Sin candidatos" description="No se encontraron resultados" />
        ) : (
          filtrados.map((c, i) => {
            const estado = ESTADO_CONFIG[c.estado] || { label: c.estado, variant: 'neutral' }
            return (
              <motion.div
                key={c.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 140px 90px 140px 80px',
                  padding: '10px 16px',
                  borderBottom: '1px solid var(--border)',
                  alignItems: 'center',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Initials nombre={c.nombre} apellidos={c.apellidos} />
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                      {c.nombre} {c.apellidos}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.email}</p>
                  </div>
                </div>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {c.vacante?.titulo || '—'}
                </span>
                <div style={{ textAlign: 'center' }}>
                  <ScoreBadge score={c.score_cv} />
                </div>
                <Badge variant={estado.variant}>{estado.label}</Badge>
                <div style={{ display: 'flex', gap: 4 }}>
                  <Button variant="secondary" size="sm" onClick={() => navigate(`/candidatos/${c.id}`)}>Ver</Button>
                </div>
              </motion.div>
            )
          })
        )}
      </Card>
    </div>
  )
}