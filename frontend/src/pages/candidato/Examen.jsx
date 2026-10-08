import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import Button from '../../components/ui/Button.jsx'

const DEMO_PREGUNTAS = [
  { id: 1, orden: 1, tipo: 'multiple_choice', enunciado: '¿Cuál de los siguientes enfoques es más adecuado para manejar autenticación en una API REST stateless?', opciones: ['Sesiones del lado del servidor', 'Basic Auth con HTTPS', 'JSON Web Tokens (JWT)', 'API Keys estáticas'] },
  { id: 2, orden: 2, tipo: 'multiple_choice', enunciado: '¿Qué estrategia evita race conditions sobre una misma fila de base de datos?', opciones: ['Ignorar el problema', 'Locking optimista', 'Reiniciar la BD', 'Variables globales'] },
  { id: 3, orden: 3, tipo: 'multiple_choice', enunciado: '¿Cuál es la principal ventaja de usar contenedores Docker?', opciones: ['Son más rápidos que una VM siempre', 'Portabilidad y consistencia entre entornos', 'Eliminan la necesidad de testing', 'Reemplazan a Git'] },
  { id: 4, orden: 4, tipo: 'multiple_choice', enunciado: '¿Qué patrón de diseño es más apropiado para desacoplar la creación de objetos complejos?', opciones: ['Singleton', 'Factory', 'Observer', 'Decorator'] },
  { id: 5, orden: 5, tipo: 'multiple_choice', enunciado: '¿Cuál es la diferencia principal entre SQL y NoSQL?', opciones: ['NoSQL siempre es más rápido', 'SQL usa esquemas rígidos, NoSQL es flexible', 'No hay diferencia real', 'SQL no soporta transacciones'] },
  { id: 6, orden: 6, tipo: 'multiple_choice', enunciado: '¿Qué hace un índice en una base de datos?', opciones: ['Borra datos duplicados', 'Acelera las consultas de lectura', 'Encripta la información', 'Valida los tipos de datos'] },
  { id: 7, orden: 7, tipo: 'abierta', enunciado: 'Explica cómo implementarías un sistema de caché para reducir la carga en un endpoint frecuentemente consultado.' },
  { id: 8, orden: 8, tipo: 'abierta', enunciado: '¿Cómo manejarías el versionado de una API REST que ya tiene clientes en producción?' },
  { id: 9, orden: 9, tipo: 'abierta', enunciado: 'Describe una situación donde hayas tenido que depurar un bug difícil de reproducir.' },
  { id: 10, orden: 10, tipo: 'abierta', enunciado: '¿Qué consideraciones tomarías al diseñar un sistema que debe escalar a millones de usuarios?' },
]

const DURACION_TOTAL = 45 * 60 // segundos

export default function Examen() {
  const navigate = useNavigate()
  const [preguntas] = useState(DEMO_PREGUNTAS)
  const [actual, setActual] = useState(0)
  const [respuestas, setRespuestas] = useState({})
  const [tiempoRestante, setTiempoRestante] = useState(DURACION_TOTAL)
  const [eventosProctoring, setEventosProctoring] = useState([])
  const timerRef = useRef(null)

  // Timer
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setTiempoRestante(t => {
        if (t <= 1) {
          clearInterval(timerRef.current)
          handleFinalizar()
          return 0
        }
        return t - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current)
  }, [])

  // Proctoring básico: detectar pérdida de foco y bloquear copy/paste, click derecho, devtools
  const registrarEvento = useCallback((tipo) => {
    setEventosProctoring(prev => [...prev, { tipo, timestamp: new Date().toISOString() }])
    api.post('/evaluaciones/candidato/examen/evento', { tipo }).catch(() => {})
  }, [])

  useEffect(() => {
    const onBlur = () => registrarEvento('perdida_foco')
    const onVisibility = () => { if (document.hidden) registrarEvento('cambio_ventana') }
    const onCopyPaste = (e) => { e.preventDefault(); registrarEvento('copy_paste'); toast.warning('Copiar y pegar no está permitido') }
    const onContextMenu = (e) => { e.preventDefault(); registrarEvento('click_derecho') }
    const onKeyDown = (e) => {
      if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I')) {
        e.preventDefault()
        registrarEvento('devtools')
      }
    }

    window.addEventListener('blur', onBlur)
    document.addEventListener('visibilitychange', onVisibility)
    document.addEventListener('copy', onCopyPaste)
    document.addEventListener('paste', onCopyPaste)
    document.addEventListener('contextmenu', onContextMenu)
    document.addEventListener('keydown', onKeyDown)

    return () => {
      window.removeEventListener('blur', onBlur)
      document.removeEventListener('visibilitychange', onVisibility)
      document.removeEventListener('copy', onCopyPaste)
      document.removeEventListener('paste', onCopyPaste)
      document.removeEventListener('contextmenu', onContextMenu)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [registrarEvento])

  function guardarRespuesta(preguntaId, valor) {
    setRespuestas(r => ({ ...r, [preguntaId]: valor }))
    // Auto-guardado incremental
    api.post('/evaluaciones/candidato/examen/respuesta', {
      pregunta_id: preguntaId, respuesta: valor,
    }).catch(() => {})
  }

  async function handleFinalizar() {
    try {
      await api.post('/evaluaciones/candidato/examen/finalizar')
    } catch {}
    navigate('/candidato/finalizado')
  }

  const pregunta = preguntas[actual]
  const minutos = Math.floor(tiempoRestante / 60)
  const segundos = tiempoRestante % 60
  const pctTiempo = (tiempoRestante / DURACION_TOTAL) * 100
  const respondidas = Object.keys(respuestas).length

  return (
    <div style={{ padding: '20px 24px', display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16, maxWidth: 1100, margin: '0 auto' }}>

      {/* Columna principal */}
      <div>
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            En curso
          </p>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>Evaluación técnica</h1>
        </div>

        {/* Timer */}
        <div style={{
          background: 'var(--text-primary)', borderRadius: 10,
          padding: '14px 16px', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', marginBottom: 16,
        }}>
          <div>
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>Tiempo restante</p>
            <p style={{
              fontSize: 22, fontWeight: 600, color: 'white',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {String(minutos).padStart(2, '0')}:{String(segundos).padStart(2, '0')}
            </p>
          </div>
          <div style={{ flex: 1, marginLeft: 20 }}>
            <div style={{ height: 3, background: 'rgba(255,255,255,0.15)', borderRadius: 999, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${pctTiempo}%`,
                background: pctTiempo < 15 ? '#EF4444' : 'white',
                borderRadius: 999, transition: 'width 1s linear',
              }} />
            </div>
          </div>
        </div>

        {/* Pregunta */}
        <motion.div
          key={pregunta.id}
          initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.15 }}
          style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 10, padding: 18, marginBottom: 14,
          }}
        >
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
            Pregunta {pregunta.orden} de {preguntas.length} · {pregunta.tipo === 'multiple_choice' ? 'Opción múltiple' : 'Abierta'}
          </p>
          <p style={{ fontSize: 15, fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: 16 }}>
            {pregunta.enunciado}
          </p>

          {pregunta.tipo === 'multiple_choice' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {pregunta.opciones.map(op => {
                const selected = respuestas[pregunta.id] === op
                return (
                  <button
                    key={op}
                    onClick={() => guardarRespuesta(pregunta.id, op)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '10px 12px', borderRadius: 8, fontSize: 13,
                      textAlign: 'left', cursor: 'pointer',
                      border: `1px solid ${selected ? 'var(--text-primary)' : 'var(--border)'}`,
                      background: selected ? 'var(--bg-page)' : 'var(--bg-card)',
                      color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontWeight: selected ? 500 : 400,
                    }}
                  >
                    <span style={{
                      width: 14, height: 14, borderRadius: '50%',
                      border: `1.5px solid ${selected ? 'var(--text-primary)' : 'var(--border-hover)'}`,
                      background: selected ? 'var(--text-primary)' : 'transparent',
                      flexShrink: 0,
                    }} />
                    {op}
                  </button>
                )
              })}
            </div>
          ) : (
            <textarea
              value={respuestas[pregunta.id] || ''}
              onChange={e => guardarRespuesta(pregunta.id, e.target.value)}
              placeholder="Escribe tu respuesta aquí..."
              rows={6}
              style={{
                width: '100%', padding: 12,
                border: '1px solid var(--border)', borderRadius: 8,
                fontSize: 13, fontFamily: 'inherit', resize: 'vertical',
                outline: 'none', color: 'var(--text-primary)',
                background: 'var(--bg-card)',
              }}
            />
          )}
        </motion.div>

        {/* Navegación */}
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            variant="secondary"
            onClick={() => setActual(a => Math.max(0, a - 1))}
            disabled={actual === 0}
          >
            Anterior
          </Button>
          {actual < preguntas.length - 1 ? (
            <Button onClick={() => setActual(a => a + 1)} style={{ flex: 1, justifyContent: 'center' }}>
              Siguiente
            </Button>
          ) : (
            <Button onClick={handleFinalizar} style={{ flex: 1, justifyContent: 'center' }}>
              Finalizar examen
            </Button>
          )}
        </div>
      </div>

      {/* Columna lateral — mapa de preguntas */}
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 10, padding: 16, height: 'fit-content',
      }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 14 }}>
          Tu progreso
        </p>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {respondidas} de {preguntas.length} respondidas
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, marginBottom: 16 }}>
          {preguntas.map((p, i) => {
            const isRespondida = respuestas[p.id] != null && respuestas[p.id] !== ''
            const isActual = i === actual
            return (
              <button
                key={p.id}
                onClick={() => setActual(i)}
                style={{
                  aspectRatio: '1', borderRadius: 6, fontSize: 11, fontWeight: 500,
                  cursor: 'pointer', border: '1px solid var(--border)',
                  background: isActual ? 'var(--text-primary)' : isRespondida ? 'var(--bg-page)' : 'var(--bg-card)',
                  color: isActual ? 'var(--bg-card)' : isRespondida ? 'var(--text-primary)' : 'var(--text-muted)',
                }}
              >
                {p.orden}
              </button>
            )
          })}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: 'var(--bg-page)', border: '1px solid var(--border)' }} />
            Respondida
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: 'var(--text-primary)' }} />
            Pregunta actual
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: 'var(--bg-card)', border: '1px solid var(--border)' }} />
            Pendiente
          </div>
        </div>
      </div>
    </div>
  )
}