import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'

const DEMO = {
  id: '1',
  candidato: { nombre: 'María', apellidos: 'Alvarado' },
  vacante: { titulo: 'Full Stack Developer' },
  nota: 16.5, estado: 'finalizado',
  semaforo: 'verde', puntaje_riesgo: 2,
  duracion_minutos: 38,
  fecha_fin: '2026-09-20T14:30:00Z',
  preguntas: [
    {
      id: 1, orden: 1, tipo: 'multiple_choice',
      enunciado: '¿Cuál de los siguientes enfoques es más adecuado para manejar autenticación en una API REST stateless?',
      opciones: ['Sesiones del lado del servidor con cookies', 'Basic Auth con HTTPS', 'JSON Web Tokens (JWT) con refresh tokens', 'API Keys estáticas'],
      respuesta_correcta: 'JSON Web Tokens (JWT) con refresh tokens',
      respuesta_candidato: 'JSON Web Tokens (JWT) con refresh tokens',
      puntos_max: 2, puntos_obtenidos: 2,
    },
    {
      id: 2, orden: 2, tipo: 'multiple_choice',
      enunciado: '¿Qué estrategia usarías para evitar race conditions en una operación concurrente sobre una misma fila de base de datos?',
      opciones: ['Ignorar el problema', 'Locking optimista con versión', 'Reiniciar la base de datos', 'Usar variables globales'],
      respuesta_correcta: 'Locking optimista con versión',
      respuesta_candidato: 'Ignorar el problema',
      puntos_max: 2, puntos_obtenidos: 0,
    },
    {
      id: 3, orden: 3, tipo: 'abierta',
      enunciado: 'Explica cómo implementarías un sistema de caché para reducir la carga en un endpoint que se consulta frecuentemente.',
      respuesta_candidato: 'Usaría Redis como capa de caché. Al recibir el request, primero verifico si existe en caché con una key basada en los parámetros, si existe lo retorno directo, si no consulto la base de datos y guardo el resultado con un TTL apropiado.',
      puntos_max: 2, puntos_obtenidos: 2,
      feedback_ia: 'Respuesta completa y técnicamente correcta. Menciona Redis, estrategia de keys y TTL, que son los elementos clave de una solución de caché bien diseñada.',
    },
    {
      id: 4, orden: 4, tipo: 'abierta',
      enunciado: '¿Cómo manejarías el versionado de una API REST que ya tiene clientes en producción?',
      respuesta_candidato: 'Agregaría un número de versión en la URL.',
      puntos_max: 2, puntos_obtenidos: 1,
      feedback_ia: 'Respuesta parcialmente correcta pero superficial. Menciona el versionado por URL pero no profundiza en estrategias de deprecación, comunicación a clientes ni versionado por header como alternativa.',
    },
  ],
  eventos: [
    { tipo: 'perdida_foco', severidad: 'media', timestamp: '2026-09-20T14:05:00Z' },
    { tipo: 'cambio_ventana', severidad: 'media', timestamp: '2026-09-20T14:12:00Z' },
  ],
}

const SEMAFORO_CONFIG = {
  verde: { bg: 'var(--success-bg)', color: 'var(--success-text)', label: 'Verde' },
  amarillo: { bg: 'var(--warning-bg)', color: 'var(--warning-text)', label: 'Amarillo' },
  rojo: { bg: 'var(--danger-bg)', color: 'var(--danger-text)', label: 'Rojo' },
}

function PuntosBadge({ obtenidos, max }) {
  const color = obtenidos === max ? 'var(--success-text)' : obtenidos === 0 ? 'var(--danger-text)' : 'var(--warning-text)'
  const bg = obtenidos === max ? 'var(--success-bg)' : obtenidos === 0 ? 'var(--danger-bg)' : 'var(--warning-bg)'
  return (
    <span style={{
      background: bg, color, fontSize: 12, fontWeight: 600,
      borderRadius: 6, padding: '3px 10px', flexShrink: 0,
    }}>
      {obtenidos}/{max} pts
    </span>
  )
}

export default function ExamenDetalle() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: e } = useQuery({
    queryKey: ['examen', id],
    queryFn: () => api.get(`/evaluaciones/examenes/${id}`).then(r => r.data).catch(() => DEMO),
  })

  const examen = e || DEMO
  const semaforo = SEMAFORO_CONFIG[examen.semaforo] || SEMAFORO_CONFIG.verde

  return (
    <div style={{ padding: '20px 24px', maxWidth: 820 }}>
      <button onClick={() => navigate('/examenes')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', fontSize: 12, marginBottom: 14, padding: 0,
      }}>← Volver a exámenes</button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
            {examen.candidato?.nombre} {examen.candidato?.apellidos}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            {examen.vacante?.titulo} · {examen.duracion_minutos} min · {new Date(examen.fecha_fin).toLocaleDateString('es-PE')}
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-1px', color: examen.nota >= 13 ? 'var(--success-text)' : 'var(--danger-text)' }}>
            {examen.nota}/20
          </p>
        </div>
      </div>

      {/* Resumen de integridad */}
      <Card style={{ marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            background: semaforo.bg, color: semaforo.color,
            fontSize: 12, fontWeight: 500, borderRadius: 6, padding: '4px 10px',
          }}>
            ● {semaforo.label} — {examen.puntaje_riesgo} pts de riesgo
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {(examen.eventos || []).length} evento{(examen.eventos || []).length !== 1 ? 's' : ''} registrado{(examen.eventos || []).length !== 1 ? 's' : ''}
          </span>
        </div>
      </Card>

      {/* Preguntas */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {(examen.preguntas || []).map((p, i) => (
          <motion.div key={p.id}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                    Pregunta {p.orden} · {p.tipo === 'multiple_choice' ? 'Opción múltiple' : 'Abierta'}
                  </p>
                  <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                    {p.enunciado}
                  </p>
                </div>
                <PuntosBadge obtenidos={p.puntos_obtenidos} max={p.puntos_max} />
              </div>

              {p.tipo === 'multiple_choice' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {(p.opciones_json || []).map(op => {
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
                  <div style={{
                    padding: 12, background: 'var(--bg-page)', borderRadius: 6,
                    fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: 10,
                  }}>
                    {p.respuesta_candidato}
                  </div>
                  {p.feedback_ia && (
                    <div style={{
                      padding: '8px 12px', borderRadius: 6,
                      background: 'var(--info-bg)', color: 'var(--info-text)',
                      fontSize: 12, lineHeight: 1.5,
                    }}>
                      <strong>Feedback IA:</strong> {p.feedback_ia}
                    </div>
                  )}
                </>
              )}
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}