import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Button from '../../components/ui/Button.jsx'

const DEMO = {
  id: '1', codigo: 'TI-2026-001', titulo: 'Full Stack Developer',
  estado: 'abierta', prioridad: 'alta',
  area: { nombre: 'Tecnología' }, cantidad_posiciones: 2,
  modalidad: 'hibrido', ciudad: 'Lima', tipo_contrato: 'indefinido',
  descripcion: 'Buscamos un desarrollador Full Stack para unirse a nuestro equipo de producto...',
  requisitos: '3+ años de experiencia con React y Node.js. Conocimiento de bases de datos relacionales.',
  tecnologias: 'React, Node.js, PostgreSQL, Docker, AWS',
  score_cv_minimo: 60, nota_minima_examen: 13,
  candidatos: [
    { id: '1', nombre: 'María', apellidos: 'Alvarado', score_cv: 87, estado: 'entrevista_pendiente' },
    { id: '2', nombre: 'Carlos', apellidos: 'Pérez', score_cv: 74, estado: 'cv_aprobado' },
  ],
}

const ESTADO_VARIANT = { abierta: 'success', pausada: 'warning', cerrada: 'neutral', borrador: 'neutral' }

const TABS = [
  { key: 'info', label: 'Información' },
  { key: 'candidatos', label: 'Candidatos' },
  { key: 'marketing', label: 'Publicación' },
]

export default function VacanteDetalle() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [tab, setTab] = useState('info')
  const [generandoTextos, setGenerandoTextos] = useState(false)
  const [textos, setTextos] = useState(null)

  const { data: v } = useQuery({
    queryKey: ['vacante', id],
    queryFn: () => api.get(`/vacantes/${id}`).then(r => r.data).catch(() => DEMO),
  })

  const vacante = v || DEMO

  async function handlePublicar() {
    try {
      await api.post(`/vacantes/${id}/publicar`)
      toast.success('Vacante publicada')
    } catch {
      toast.error('Error al publicar')
    }
  }

  async function handleGenerarTextos() {
    setGenerandoTextos(true)
    try {
      const { data } = await api.post(`/vacantes/${id}/generar-textos`)
      setTextos(data.textos)
    } catch {
      toast.error('Error al generar los textos')
    } finally {
      setGenerandoTextos(false)
    }
  }

  return (
    <div style={{ padding: '20px 24px', maxWidth: 900 }}>
      <button onClick={() => navigate('/vacantes')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', fontSize: 12, marginBottom: 14, padding: 0,
      }}>← Volver a vacantes</button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{vacante.titulo}</h1>
            <Badge variant={ESTADO_VARIANT[vacante.estado]}>{vacante.estado}</Badge>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {vacante.codigo} · {vacante.area?.nombre} · {vacante.ciudad} · {vacante.modalidad}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="secondary" onClick={() => navigate(`/vacantes/${id}/editar`)}>Editar</Button>
          {vacante.estado === 'borrador' && <Button onClick={handlePublicar}>Publicar</Button>}
          {vacante.estado === 'abierta' && <Button variant="secondary">Pausar</Button>}
        </div>
      </div>

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

      <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>

        {tab === 'info' && (
          <Card>
            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Descripción
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 18 }}>
              {vacante.descripcion}
            </p>

            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Requisitos
            </p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 18 }}>
              {vacante.requisitos}
            </p>

            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Tecnologías
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
              {(vacante.tecnologias || '').split(',').map(t => t.trim()).filter(Boolean).map(t => (
                <Badge key={t} variant="info">{t}</Badge>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>Posiciones</p>
                <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{vacante.cantidad_posiciones}</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>Score CV mínimo</p>
                <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{vacante.score_cv_minimo}/100</p>
              </div>
              <div>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>Nota examen mínima</p>
                <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{vacante.nota_minima_examen}/20</p>
              </div>
            </div>
          </Card>
        )}

        {tab === 'candidatos' && (
          <Card padding="0">
            {(vacante.candidatos || []).length === 0 ? (
              <p style={{ textAlign: 'center', padding: 32, fontSize: 13, color: 'var(--text-muted)' }}>
                Aún no hay candidatos para esta vacante
              </p>
            ) : vacante.candidatos.map((c, i) => (
              <div key={c.id} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px',
                borderBottom: i < vacante.candidatos.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'var(--bg-page)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)',
                }}>{c.nombre[0]}{c.apellidos[0]}</div>
                <span style={{ flex: 1, fontSize: 13, color: 'var(--text-primary)' }}>
                  {c.nombre} {c.apellidos}
                </span>
                <Badge variant="info">{c.score_cv}</Badge>
                <Button variant="secondary" size="sm" onClick={() => navigate(`/candidatos/${c.id}`)}>Ver</Button>
              </div>
            ))}
          </Card>
        )}

        {tab === 'marketing' && (
          <Card>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14 }}>
              Genera textos optimizados para publicar esta vacante en distintas plataformas.
            </p>
            <Button onClick={handleGenerarTextos} disabled={generandoTextos}>
              {generandoTextos ? 'Generando...' : 'Generar textos con IA'}
            </Button>

            {textos && (
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Object.entries(textos).map(([plataforma, texto]) => (
                  <div key={plataforma} style={{ padding: 12, background: 'var(--bg-page)', borderRadius: 6 }}>
                    <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                      {plataforma}
                    </p>
                    <p style={{ fontSize: 13, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{texto}</p>
                  </div>
                ))}
              </div>
            )}

            <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Feed XML para Indeed</p>
              <code style={{
                display: 'block', padding: 10, background: 'var(--bg-page)',
                borderRadius: 6, fontSize: 12, color: 'var(--text-secondary)',
                wordBreak: 'break-all',
              }}>
                {window.location.origin}/api/vacantes/{id}/feed-xml
              </code>
            </div>
          </Card>
        )}
      </motion.div>
    </div>
  )
}