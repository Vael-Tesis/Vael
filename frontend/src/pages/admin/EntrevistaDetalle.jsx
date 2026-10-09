import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'

const DEMO = {
  id: '1',
  candidato: { nombre: 'Jorge', apellidos: 'Torres' },
  vacante: { titulo: 'DevOps Engineer' },
  nota: 16.8, estado: 'finalizada',
  duracion_minutos: 22,
  audio_url: null,
  dimensiones: {
    claridad_expresion: { nota: 17, peso: 20, justificacion: 'Se expresa de forma clara y estructurada, con pausas apropiadas y vocabulario técnico preciso.' },
    coherencia_respuestas: { nota: 16, peso: 20, justificacion: 'Sus respuestas mantienen consistencia lógica a lo largo de la entrevista, sin contradicciones.' },
    precision_tecnica: { nota: 18, peso: 30, justificacion: 'Demuestra conocimiento sólido y profundo en las tecnologías de infraestructura preguntadas.' },
    comunicacion_efectiva: { nota: 16, peso: 20, justificacion: 'Transmite sus ideas de manera profesional y es fácil de seguir.' },
    seguridad_confianza: { nota: 15, peso: 10, justificacion: 'Responde con seguridad en temas técnicos, algo más dubitativo en preguntas situacionales.' },
  },
  transcripcion: [
    { hablante: 'EVA', texto: 'Hola Jorge, bienvenido a tu entrevista para la posición de DevOps Engineer. Cuéntame, ¿qué te motivó a postular a esta vacante?' },
    { hablante: 'Candidato', texto: 'Hola, gracias por la oportunidad. Me atrajo mucho el enfoque en automatización e infraestructura como código que mencionan en la descripción del puesto.' },
    { hablante: 'EVA', texto: '¿Puedes contarme sobre algún proyecto donde hayas implementado CI/CD desde cero?' },
    { hablante: 'Candidato', texto: 'Sí, en mi trabajo anterior implementamos un pipeline completo con GitHub Actions que iba desde el build hasta el despliegue en ECS, incluyendo tests automatizados y rollback en caso de fallas.' },
  ],
}

const DIMENSIONES_LABEL = {
  claridad_expresion: 'Claridad de expresión',
  coherencia_respuestas: 'Coherencia de respuestas',
  precision_tecnica: 'Precisión técnica',
  comunicacion_efectiva: 'Comunicación efectiva',
  seguridad_confianza: 'Seguridad y confianza',
}

function DimensionBar({ label, nota, peso, justificacion }) {
  const pct = (nota / 20) * 100
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
          {label} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>· peso {peso}%</span>
        </span>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{nota}/20</span>
      </div>
      <div style={{ height: 4, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden', marginBottom: 6 }}>
        <motion.div
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ height: '100%', background: 'var(--text-primary)', borderRadius: 999 }}
        />
      </div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>{justificacion}</p>
    </div>
  )
}

export default function EntrevistaDetalle() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: e } = useQuery({
    queryKey: ['entrevista', id],
    queryFn: () => api.get(`/entrevista/detalle/${id}`).then(r => r.data).catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const entrevista = e || DEMO

  return (
    <div style={{ padding: '20px 24px', maxWidth: 900 }}>
      <button onClick={() => navigate('/entrevistas')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', fontSize: 12, marginBottom: 14, padding: 0,
      }}>← Volver a entrevistas</button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
            {entrevista.candidato?.nombre} {entrevista.candidato?.apellidos}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            {entrevista.vacante?.titulo} · {entrevista.duracion_minutos} min
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-1px', color: entrevista.nota >= 13 ? 'var(--success-text)' : 'var(--danger-text)' }}>
            {entrevista.nota}/20
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Columna izquierda — Dimensiones */}
        <div>
          <Card style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Análisis multidimensional
            </p>
            {Object.entries(entrevista.dimensiones || {}).map(([key, val]) => (
              <DimensionBar key={key} label={DIMENSIONES_LABEL[key] || key} {...val} />
            ))}
          </Card>

          {entrevista.audio_url ? (
            <Card>
              <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Audio de la entrevista
              </p>
              <audio controls style={{ width: '100%' }} src={entrevista.audio_url} />
            </Card>
          ) : (
            <Card>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>
                Audio no disponible
              </p>
            </Card>
          )}
        </div>

        {/* Columna derecha — Transcripción */}
        <Card style={{ maxHeight: 560, overflowY: 'auto' }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Transcripción
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(entrevista.transcripcion || []).map((linea, i) => (
              <div key={i} style={{
                display: 'flex', flexDirection: 'column',
                alignItems: linea.hablante === 'EVA' ? 'flex-start' : 'flex-end',
              }}>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>
                  {linea.hablante}
                </span>
                <div style={{
                  maxWidth: '85%', padding: '8px 12px', borderRadius: 8,
                  fontSize: 13, lineHeight: 1.4,
                  background: linea.hablante === 'EVA' ? 'var(--bg-page)' : 'var(--text-primary)',
                  color: linea.hablante === 'EVA' ? 'var(--text-primary)' : 'var(--bg-card)',
                }}>
                  {linea.texto}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}