import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'

const METRICS = [
  { key: 'vacantes_activas',        label: 'Vacantes activas' },
  { key: 'candidatos_nuevos',       label: 'Candidatos nuevos' },
  { key: 'evaluaciones_pendientes', label: 'Evaluaciones pendientes' },
  { key: 'finalistas',              label: 'Finalistas' },
]

const FUNNEL = [
  { label: 'Postulaciones',   key: 'total_postulaciones', color: '#0a0a0a' },
  { label: 'CV aprobados',    key: 'cv_aprobados',        color: '#0a0a0a' },
  { label: 'Examen aprobado', key: 'examen_aprobados',    color: '#0a0a0a' },
  { label: 'En entrevista',   key: 'en_entrevista',       color: '#0a0a0a' },
  { label: 'Finalistas',      key: 'finalistas',          color: '#166534' },
]

// Estados que cuentan como "evaluación pendiente" (examen o entrevista por rendir)
const ESTADOS_EVALUACION_PENDIENTE = ['examen_pendiente', 'entrevista_pendiente']
// Candidato "nuevo": postuló en los últimos 7 días
const DIAS_CANDIDATO_NUEVO = 7

// Datos demo para cuando el backend no responde aún (modo desarrollo)
const DEMO = {
  vacantes_activas: 12,
  candidatos_nuevos: 34,
  evaluaciones_pendientes: 19,
  total_postulaciones: 248,
  cv_aprobados: 91,
  examen_aprobados: 52,
  en_entrevista: 24,
  finalistas: 8,
  candidatos_recientes: [
    { id: 1, nombre: 'María', apellidos: 'Alvarado', score_cv: 87, estado: 'entrevista_pendiente', vacante_codigo: 'TI-2026-001' },
    { id: 2, nombre: 'Carlos', apellidos: 'Pérez',   score_cv: 74, estado: 'cv_aprobado',         vacante_codigo: 'TI-2026-001' },
    { id: 3, nombre: 'Lucía',  apellidos: 'Ramírez', score_cv: 61, estado: 'examen_pendiente',    vacante_codigo: 'DIS-2026-002' },
    { id: 4, nombre: 'Jorge',  apellidos: 'Torres',  score_cv: 92, estado: 'entrevista_pendiente', vacante_codigo: 'TI-2026-003' },
  ],
}

/** Combina vacantes + candidatos (ya traídos del backend) en las métricas que muestra el dashboard. */
function calcularMetricas(vacantes, candidatos) {
  const vacantePorId = new Map(vacantes.map(v => [v.id, v]))
  const hace7dias = Date.now() - DIAS_CANDIDATO_NUEVO * 24 * 60 * 60 * 1000

  const total_postulaciones = candidatos.length
  const cv_aprobados = candidatos.filter(c => c.score_cv != null && c.score_cv >= 60).length
  const examen_aprobados = candidatos.filter(c =>
    ['examen_aprobado', 'entrevista_pendiente', 'entrevista_realizada', 'finalista', 'contratado'].includes(c.estado)
  ).length
  const en_entrevista = candidatos.filter(c =>
    ['entrevista_pendiente', 'entrevista_realizada'].includes(c.estado)
  ).length
  const finalistas = candidatos.filter(c => c.es_finalista || c.estado === 'finalista').length
  const evaluaciones_pendientes = candidatos.filter(c => ESTADOS_EVALUACION_PENDIENTE.includes(c.estado)).length
  const candidatos_nuevos = candidatos.filter(c => {
    const fecha = c.fecha_postulacion ? new Date(c.fecha_postulacion).getTime() : null
    return fecha != null && fecha >= hace7dias
  }).length

  const candidatos_recientes = [...candidatos]
    .sort((a, b) => new Date(b.fecha_postulacion) - new Date(a.fecha_postulacion))
    .slice(0, 6)
    .map(c => ({
      ...c,
      vacante_codigo: vacantePorId.get(c.vacante_id)?.codigo || '—',
    }))

  return {
    vacantes_activas: vacantes.filter(v => v.estado === 'abierta').length,
    candidatos_nuevos,
    evaluaciones_pendientes,
    total_postulaciones,
    cv_aprobados,
    examen_aprobados,
    en_entrevista,
    finalistas,
    candidatos_recientes,
  }
}

const ESTADO_BADGE = {
  entrevista_pendiente: { label: 'Entrevista', bg: 'var(--info-bg)',    color: 'var(--info-text)' },
  cv_aprobado:          { label: 'CV aprobado', bg: 'var(--success-bg)', color: 'var(--success-text)' },
  examen_pendiente:     { label: 'Examen pend.', bg: 'var(--warning-bg)', color: 'var(--warning-text)' },
  finalista:            { label: 'Finalista',   bg: 'var(--success-bg)', color: 'var(--success-text)' },
}

function ScoreBadge({ score }) {
  const bg = score >= 80 ? 'var(--success-bg)'
           : score >= 60 ? 'var(--warning-bg)'
           : 'var(--danger-bg)'
  const color = score >= 80 ? 'var(--success-text)'
              : score >= 60 ? 'var(--warning-text)'
              : 'var(--danger-text)'
  return (
    <span style={{
      background: bg, color, fontSize: 11, fontWeight: 600,
      borderRadius: 4, padding: '2px 7px',
    }}>{score}</span>
  )
}

function Initials({ nombre, apellidos }) {
  return (
    <div style={{
      width: 30, height: 30, borderRadius: '50%',
      background: 'var(--bg-page)',
      border: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)',
      flexShrink: 0,
    }}>
      {(nombre?.[0] || '') + (apellidos?.[0] || '')}
    </div>
  )
}

const card = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border)',
  borderRadius: 8,
}

export default function Dashboard() {
  const { data } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => Promise.all([
      api.get('/vacantes', { params: { limit: 500 } }),
      api.get('/candidatos', { params: { limit: 500 } }),
    ])
      .then(([vacantesRes, candidatosRes]) => calcularMetricas(vacantesRes.data, candidatosRes.data))
      .catch(() => DEMO),
  })

  const d = data || DEMO
  const total = d.total_postulaciones || 1

  return (
    <div style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>Dashboard</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
          Resumen del proceso de selección
        </p>
      </div>

      {/* Métricas */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 16 }}>
        {METRICS.map((m, i) => (
          <motion.div
            key={m.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.2 }}
            style={{ ...card, padding: '14px 16px' }}
          >
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{m.label}</p>
            <p style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.5px', color: 'var(--text-primary)' }}>
              {d[m.key] ?? '—'}
            </p>
          </motion.div>
        ))}
      </div>

      {/* Candidatos + Embudo */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 12 }}>

        {/* Candidatos recientes */}
        <div style={card}>
          <div style={{
            padding: '11px 16px',
            borderBottom: '1px solid var(--border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
              Candidatos recientes
            </span>
            <a href="/candidatos" style={{ fontSize: 12, color: 'var(--text-muted)', textDecoration: 'none' }}>
              Ver todos
            </a>
          </div>
          {(d.candidatos_recientes || []).map((c) => {
            const badge = ESTADO_BADGE[c.estado] || { label: c.estado, bg: 'var(--bg-page)', color: 'var(--text-muted)' }
            return (
              <div key={c.id} style={{
                padding: '10px 16px',
                borderBottom: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <Initials nombre={c.nombre} apellidos={c.apellidos} />
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                    {c.nombre} {c.apellidos}
                  </p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.vacante_codigo}</p>
                </div>
                {c.score_cv != null && <ScoreBadge score={c.score_cv} />}
                <span style={{
                  fontSize: 11, fontWeight: 500, borderRadius: 4,
                  padding: '2px 7px',
                  background: badge.bg, color: badge.color,
                }}>
                  {badge.label}
                </span>
              </div>
            )
          })}
        </div>

        {/* Embudo */}
        <div style={card}>
          <div style={{ padding: '11px 16px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
              Embudo de selección
            </span>
          </div>
          <div style={{ padding: '4px 0' }}>
            {FUNNEL.map((f) => {
              const val = d[f.key] ?? 0
              const pct = Math.round((val / total) * 100)
              return (
                <div key={f.key} style={{ padding: '9px 16px' }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    fontSize: 12, marginBottom: 5,
                  }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{f.label}</span>
                    <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{val}</span>
                  </div>
                  <div style={{
                    height: 4, background: 'var(--bg-page)',
                    borderRadius: 999, overflow: 'hidden',
                  }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.6, ease: 'easeOut' }}
                      style={{ height: '100%', background: f.color, borderRadius: 999 }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}