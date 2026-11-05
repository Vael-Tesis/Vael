import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import Spinner from '../../components/ui/Spinner'
import { Volver } from '../../components/ui/Formulario'
import { useVacantes } from './evaluacionesComun'

/**
 * P-14 Detalle de entrevista (HU-19, RF-A-16): análisis multidimensional, audio, transcripción
 * y galería de capturas de auditoría. Sin datos de emociones (DEC-001): las dimensiones
 * evalúan contenido de las respuestas, nunca el tono o el estado de ánimo del candidato.
 */

interface LineaTranscripcion {
  hablante: string
  texto: string
}

/** La transcripción se guarda como texto libre con líneas "EVA: ..." / "Candidato: ...".
 * Si no sigue ese formato (texto libre de otro origen), se muestra tal cual, sin dividir. */
function analizarTranscripcion(texto: string): LineaTranscripcion[] | null {
  const lineas = texto.split('\n').map((l) => l.trim()).filter(Boolean)
  const patron = /^(EVA|Candidato):\s*(.+)$/i
  const analizadas = lineas.map((linea) => linea.match(patron))
  if (analizadas.length === 0 || analizadas.some((m) => m === null)) return null
  return analizadas.map((m) => ({ hablante: m![1], texto: m![2] }))
}

function DimensionBar({ label, nota, puntajeMaximo, peso, comentario }: { label: string; nota: number; puntajeMaximo: number; peso: number; comentario: string }) {
  const pct = puntajeMaximo > 0 ? (nota / puntajeMaximo) * 100 : 0
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
          {label} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>· peso {peso}%</span>
        </span>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{nota}/{puntajeMaximo}</span>
      </div>
      <div style={{ height: 4, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden', marginBottom: 6 }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ height: '100%', background: 'var(--text-primary)', borderRadius: 999 }} />
      </div>
      {comentario && <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.4 }}>{comentario}</p>}
    </div>
  )
}

export default function EntrevistaDetalle() {
  const { id = '' } = useParams()
  const navigate = useNavigate()

  const entrevista = useQuery({
    queryKey: ['entrevista', id],
    queryFn: async () => datos(await api.GET('/api/entrevista/detalle/{entrevista_id}', { params: { path: { entrevista_id: id } } }), 'No se pudo cargar la entrevista'),
  })
  const vacantes = useVacantes()

  if (entrevista.isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
  if (entrevista.error || !entrevista.data) {
    return <Card><EmptyState title="No se pudo cargar la entrevista" description={mensajeDe(entrevista.error, 'Intenta de nuevo')} /></Card>
  }

  const e = entrevista.data
  const vacante = (vacantes.data ?? []).find((v) => v.id === e.vacante_id)
  const dimensiones = Object.entries(e.dimensiones_json ?? {}) as [string, { nota: number; puntaje_maximo: number; peso: number; comentario: string }][]
  const lineas = e.transcripcion ? analizarTranscripcion(e.transcripcion) : null

  return (
    <div style={{ padding: '20px 24px', maxWidth: 900 }}>
      <Volver onClick={() => navigate('/entrevistas')}>Volver a entrevistas</Volver>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{e.candidato_nombre} {e.candidato_apellidos}</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            {vacante?.titulo ?? 'Vacante'}{e.duracion_minutos != null && ` · ${e.duracion_minutos} min`}
          </p>
        </div>
        <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-1px', color: e.nota != null && e.nota >= 13 ? 'var(--success-text)' : 'var(--danger-text)' }}>
          {e.nota != null ? `${e.nota.toFixed(1)}/20` : '—'}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <Card style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Análisis multidimensional
            </p>
            {dimensiones.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin análisis todavía</p>
            ) : (
              dimensiones.map(([nombre, val]) => (
                <DimensionBar key={nombre} label={nombre} nota={val.nota} puntajeMaximo={val.puntaje_maximo} peso={val.peso} comentario={val.comentario} />
              ))
            )}
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Audio de la entrevista
            </p>
            {e.audio_url ? (
              <audio controls style={{ width: '100%' }} src={e.audio_url} />
            ) : (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>Audio no disponible</p>
            )}
          </Card>

          <Card>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Capturas de auditoría ({e.capturas.length})
            </p>
            {e.capturas.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>Sin capturas registradas</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                {e.capturas.map((c) => (
                  <a key={c.id} href={c.imagen_url} target="_blank" rel="noreferrer" title={`${c.tipo} · ${new Date(c.timestamp).toLocaleTimeString('es-PE')}`}>
                    <img src={c.imagen_url} alt={c.tipo} style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border)' }} />
                  </a>
                ))}
              </div>
            )}
          </Card>
        </div>

        <Card style={{ maxHeight: 560, overflowY: 'auto' }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Transcripción
          </p>
          {!e.transcripcion ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin transcripción todavía</p>
          ) : lineas ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {lineas.map((linea, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: linea.hablante.toLowerCase() === 'eva' ? 'flex-start' : 'flex-end' }}>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>{linea.hablante}</span>
                  <div style={{
                    maxWidth: '85%', padding: '8px 12px', borderRadius: 8, fontSize: 13, lineHeight: 1.4,
                    background: linea.hablante.toLowerCase() === 'eva' ? 'var(--bg-page)' : 'var(--text-primary)',
                    color: linea.hablante.toLowerCase() === 'eva' ? 'var(--text-primary)' : 'var(--bg-card)',
                  }}>
                    {linea.texto}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{e.transcripcion}</p>
          )}
        </Card>
      </div>
    </div>
  )
}
