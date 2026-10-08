import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Button from '../../components/ui/Button.jsx'

const DEMO = {
  id: '1', nombre: 'María', apellidos: 'Alvarado',
  email: 'maria.alvarado@gmail.com', telefono: '+51 987 654 321',
  linkedin: 'linkedin.com/in/mariaalvarado', github: 'github.com/mariaalvarado',
  estado: 'entrevista_pendiente',
  vacante: { titulo: 'Full Stack Developer', codigo: 'TI-2026-001' },
  score_cv: 87, match_porcentaje: 82,
  clasificacion_ia: 'altamente_recomendado',
  resumen_ia: 'Desarrolladora Full Stack con 4 años de experiencia en React y Node.js. Sólida trayectoria en proyectos de e-commerce y fintech. Buen match con los requisitos técnicos de la vacante, especialmente en el stack de JavaScript moderno.',
  habilidades_detectadas: ['React', 'Node.js', 'TypeScript', 'PostgreSQL', 'Docker', 'AWS'],
  inconsistencias: ['Gap de 5 meses entre 2023 y 2024 sin explicación'],
  examen: { nota: 16.5, semaforo: 'verde', puntaje_riesgo: 2, fecha_fin: '2026-09-20T14:30:00Z' },
  entrevista: { nota: 15.2, estado: 'pendiente', audio_url: null,
    dimensiones: { claridad_expresion: 16, coherencia_respuestas: 15, precision_tecnica: 14, comunicacion_efectiva: 16, seguridad_confianza: 15 } },
  score_final: 16.1,
  notas: [
    { id: 1, autor: 'Gabriel Llanos', contenido: 'Muy buena comunicación en la llamada inicial de coordinación.', created_at: '2026-09-21T09:00:00Z' },
  ],
  tags: ['Prioritario', 'React Senior'],
}

const TABS = [
  { key: 'resumen',    label: 'Resumen' },
  { key: 'examen',     label: 'Examen' },
  { key: 'entrevista', label: 'Entrevista' },
  { key: 'notas',      label: 'Notas' },
]

const CLASIFICACION_CONFIG = {
  altamente_recomendado: { label: 'Altamente recomendado', variant: 'success' },
  recomendado:           { label: 'Recomendado',           variant: 'info' },
  requiere_revision:     { label: 'Requiere revisión',     variant: 'warning' },
  no_apto:               { label: 'No apto',               variant: 'danger' },
}

function ScoreCircle({ value, max = 100, label }) {
  const pct = Math.round((value / max) * 100)
  const color = pct >= 80 ? 'var(--success-text)' : pct >= 60 ? 'var(--warning-text)' : 'var(--danger-text)'
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        width: 64, height: 64, borderRadius: '50%',
        border: `3px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 6px',
      }}>
        <span style={{ fontSize: 18, fontWeight: 600, color }}>{value}</span>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</p>
    </div>
  )
}

export default function CandidatoDetalle() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState('resumen')

  const { data: c } = useQuery({
    queryKey: ['candidato', id],
    queryFn: () => api.get(`/candidatos/${id}`).then(r => r.data).catch(() => DEMO),
  })

  const candidato = c || DEMO
  const clasificacion = CLASIFICACION_CONFIG[candidato.clasificacion_ia] || CLASIFICACION_CONFIG.recomendado

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1100 }}>
      {/* Volver */}
      <button onClick={() => navigate('/candidatos')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', fontSize: 12, marginBottom: 14,
        display: 'flex', alignItems: 'center', gap: 4, padding: 0,
      }}>
        ← Volver a candidatos
      </button>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 14 }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%',
            background: 'var(--bg-page)', border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)', flexShrink: 0,
          }}>
            {candidato.nombre[0]}{candidato.apellidos[0]}
          </div>
          <div>
            <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
              {candidato.nombre} {candidato.apellidos}
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
              {candidato.vacante?.titulo} · {candidato.vacante?.codigo}
            </p>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <Badge variant={clasificacion.variant}>{clasificacion.label}</Badge>
              {(candidato.tags || []).map(t => (
                <Badge key={t} variant="neutral">{t}</Badge>
              ))}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="secondary">Reenviar correo</Button>
          <Button variant="primary">Marcar finalista</Button>
        </div>
      </div>

      {/* Info de contacto */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>Email</p>
            <p style={{ fontSize: 13, color: 'var(--text-primary)' }}>{candidato.email}</p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>Teléfono</p>
            <p style={{ fontSize: 13, color: 'var(--text-primary)' }}>{candidato.telefono || '—'}</p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>LinkedIn</p>
            <p style={{ fontSize: 13, color: 'var(--text-primary)' }}>{candidato.linkedin || '—'}</p>
          </div>
          <div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>GitHub</p>
            <p style={{ fontSize: 13, color: 'var(--text-primary)' }}>{candidato.github || '—'}</p>
          </div>
        </div>
      </Card>

      {/* Scores */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
          <ScoreCircle value={candidato.score_cv} max={100} label="Score CV" />
          <div style={{ width: 1, height: 40, background: 'var(--border)' }} />
          <ScoreCircle value={candidato.examen?.nota || 0} max={20} label="Nota examen" />
          <div style={{ width: 1, height: 40, background: 'var(--border)' }} />
          <ScoreCircle value={candidato.entrevista?.nota || 0} max={20} label="Nota entrevista" />
          <div style={{ width: 1, height: 40, background: 'var(--border)' }} />
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: 28, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-1px' }}>
              {candidato.score_final?.toFixed(1) || '—'}
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Score final</p>
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 16 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            padding: '8px 14px', fontSize: 13, fontWeight: 500,
            color: tab === t.key ? 'var(--text-primary)' : 'var(--text-muted)',
            borderBottom: tab === t.key ? '2px solid var(--text-primary)' : '2px solid transparent',
            marginBottom: -1,
          }}>{t.label}</button>
        ))}
      </div>

      {/* Contenido de tabs */}
      <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>

        {tab === 'resumen' && (
          <Card>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Resumen generado por IA
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 20 }}>
              {candidato.resumen_ia}
            </p>

            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Habilidades detectadas
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
              {(candidato.habilidades_detectadas || []).map(h => (
                <Badge key={h} variant="info">{h}</Badge>
              ))}
            </div>

            {candidato.inconsistencias?.length > 0 && (
              <>
                <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Inconsistencias detectadas
                </p>
                {candidato.inconsistencias.map((inc, i) => (
                  <div key={i} style={{
                    background: 'var(--warning-bg)', color: 'var(--warning-text)',
                    padding: '8px 12px', borderRadius: 6, fontSize: 12, marginBottom: 6,
                  }}>
                    ⚠ {inc}
                  </div>
                ))}
              </>
            )}
          </Card>
        )}

        {tab === 'examen' && (
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                  Nota: {candidato.examen?.nota}/20
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Finalizado el {new Date(candidato.examen?.fecha_fin).toLocaleDateString('es-PE')}
                </p>
              </div>
              <Badge variant={candidato.examen?.semaforo === 'verde' ? 'success' : candidato.examen?.semaforo === 'amarillo' ? 'warning' : 'danger'}>
                ● Riesgo: {candidato.examen?.puntaje_riesgo} pts
              </Badge>
            </div>
            <Button variant="secondary" size="sm">Ver preguntas y respuestas</Button>
          </Card>
        )}

        {tab === 'entrevista' && (
          <Card>
            {candidato.entrevista?.estado === 'pendiente' ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 24 }}>
                El candidato aún no ha realizado la entrevista
              </p>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
                  {Object.entries(candidato.entrevista?.dimensiones || {}).map(([key, val]) => (
                    <div key={key}>
                      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'capitalize' }}>
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{val}</p>
                    </div>
                  ))}
                </div>
                {candidato.entrevista?.audio_url && (
                  <audio controls style={{ width: '100%' }} src={candidato.entrevista.audio_url} />
                )}
              </>
            )}
          </Card>
        )}

        {tab === 'notas' && (
          <Card>
            <textarea
              placeholder="Escribe una nota interna sobre este candidato..."
              style={{
                width: '100%', minHeight: 70, padding: 10,
                border: '1px solid var(--border)', borderRadius: 6,
                fontSize: 13, fontFamily: 'inherit', resize: 'vertical',
                marginBottom: 10, outline: 'none',
              }}
            />
            <Button size="sm" style={{ marginBottom: 16 }}>Agregar nota</Button>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {(candidato.notas || []).map(n => (
                <div key={n.id} style={{
                  padding: 10, background: 'var(--bg-page)', borderRadius: 6,
                }}>
                  <p style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4 }}>{n.contenido}</p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {n.autor} · {new Date(n.created_at).toLocaleDateString('es-PE')}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </motion.div>
    </div>
  )
}