import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'

const DEMO = {
  fases: [
    { nombre: 'Análisis de CV', estado: 'completada', descripcion: 'Tu CV fue revisado' },
    { nombre: 'Examen técnico', estado: 'completada', descripcion: 'Evaluación finalizada' },
    { nombre: 'Entrevista con EVA', estado: 'en_curso', descripcion: 'Pendiente de realizar' },
    { nombre: 'Evaluación final', estado: 'pendiente', descripcion: 'En espera de resultados' },
    { nombre: 'Resultado', estado: 'pendiente', descripcion: 'Te notificaremos por correo' },
  ],
}

const candidatoData = JSON.parse(sessionStorage.getItem('vael_candidate_data') || '{}')

function FaseIcon({ estado }) {
  const config = {
    completada: { bg: 'var(--success-bg)', color: 'var(--success-text)', icon: '✓' },
    en_curso:   { bg: 'var(--text-primary)', color: 'var(--bg-card)', icon: '●' },
    pendiente:  { bg: 'var(--bg-page)', color: 'var(--text-muted)', icon: '○' },
  }
  const c = config[estado] || config.pendiente
  return (
    <div style={{
      width: 28, height: 28, borderRadius: '50%',
      background: c.bg, color: c.color,
      border: estado === 'pendiente' ? '1.5px solid var(--border)' : 'none',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12, flexShrink: 0,
    }}>{c.icon}</div>
  )
}

export default function Progreso() {
  const candidatoData = JSON.parse(sessionStorage.getItem('vael_candidate_data') || '{}')
  const { data } = useQuery({
    queryKey: ['progreso'],
    queryFn: () => api.get('/evaluaciones/candidato/progreso').then(r => r.data).catch(() => DEMO),
  })

  const progreso = data || DEMO

  return (
    <div style={{
      minHeight: 'calc(100vh - 52px)', display: 'flex',
      justifyContent: 'center', padding: '40px 20px',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        style={{ width: '100%', maxWidth: 480 }}
      >
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
            Tu proceso de selección
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
            {candidatoData.vacante?.titulo || 'Seguimiento de tu postulación'}
          </p>
        </div>

        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 24,
        }}>
          {progreso.fases.map((fase, i) => (
            <div key={fase.nombre} style={{ display: 'flex', gap: 12 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <FaseIcon estado={fase.estado} />
                {i < progreso.fases.length - 1 && (
                  <div style={{
                    width: 1.5, flex: 1, minHeight: 32,
                    background: fase.estado === 'completada' ? 'var(--success-text)' : 'var(--border)',
                    margin: '4px 0',
                  }} />
                )}
              </div>
              <div style={{ paddingBottom: 24 }}>
                <p style={{
                  fontSize: 13, fontWeight: 500,
                  color: fase.estado === 'pendiente' ? 'var(--text-muted)' : 'var(--text-primary)',
                }}>
                  {fase.nombre}
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {fase.descripcion}
                </p>
              </div>
            </div>
          ))}
        </div>

        <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', marginTop: 16 }}>
          Te notificaremos por correo en cada avance de tu proceso
        </p>
      </motion.div>
    </div>
  )
}