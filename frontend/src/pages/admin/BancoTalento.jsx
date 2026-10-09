import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Button from '../../components/ui/Button.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import Spinner from '../../components/ui/Spinner.jsx'

const DEMO = [
  { id: '11', nombre: 'Sofía', apellidos: 'Castillo', score_cv: 83, clasificacion_ia: 'altamente_recomendado', area: { nombre: 'Tecnología' }, vacante_anterior: { titulo: 'Backend Engineer' }, habilidades_detectadas: ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'AWS', 'Redis'] },
  { id: '12', nombre: 'Diego', apellidos: 'Quispe', score_cv: 76, clasificacion_ia: 'recomendado', area: { nombre: 'Tecnología' }, vacante_anterior: { titulo: 'Full Stack Developer' }, habilidades_detectadas: ['React', 'Node.js', 'TypeScript'] },
  { id: '13', nombre: 'Valeria', apellidos: 'Ríos', score_cv: 71, clasificacion_ia: 'recomendado', area: { nombre: 'Diseño' }, vacante_anterior: { titulo: 'UX Designer' }, habilidades_detectadas: ['Figma', 'Investigación UX', 'Prototipado'] },
  { id: '14', nombre: 'Mateo', apellidos: 'Salas', score_cv: 68, clasificacion_ia: 'requiere_revision', area: { nombre: 'Comercial' }, vacante_anterior: { titulo: 'Sales Executive' }, habilidades_detectadas: ['Negociación', 'CRM', 'Prospección'] },
]

const CLASIFICACION = {
  altamente_recomendado: { label: 'Altamente recomendado', variant: 'success' },
  recomendado:           { label: 'Recomendado',           variant: 'info' },
  requiere_revision:     { label: 'Requiere revisión',     variant: 'warning' },
  no_apto:               { label: 'No apto',               variant: 'danger' },
}

// El backend guarda las habilidades como texto JSON; aceptamos ambos formatos
function parseHabilidades(v) {
  if (Array.isArray(v)) return v
  try { return JSON.parse(v) || [] } catch { return [] }
}

const selectStyle = {
  height: 36, padding: '0 12px', border: '1px solid var(--border)',
  borderRadius: 6, background: 'var(--bg-card)', color: 'var(--text-primary)',
  fontSize: 13, outline: 'none',
}

export default function BancoTalento() {
  const navigate = useNavigate()
  const [busqueda, setBusqueda] = useState('')
  const [scoreMin, setScoreMin] = useState('0')
  const [area, setArea] = useState('todas')

  const { data, isLoading } = useQuery({
    queryKey: ['banco-talento'],
    queryFn: () => api.get('/candidatos/banco-talento').then(r => r.data).catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const lista = data || DEMO
  const areas = [...new Set(lista.map(c => c.area?.nombre).filter(Boolean))]

  const filtrados = lista.filter(c => {
    const texto = `${c.nombre} ${c.apellidos} ${parseHabilidades(c.habilidades_detectadas).join(' ')}`.toLowerCase()
    return texto.includes(busqueda.toLowerCase())
      && (c.score_cv ?? 0) >= Number(scoreMin)
      && (area === 'todas' || c.area?.nombre === area)
  })

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Banco de talento"
        description="Candidatos de procesos anteriores con buen desempeño, listos para futuras vacantes"
      />

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          value={busqueda} onChange={e => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre o habilidad..."
          style={{ ...selectStyle, width: 280 }}
        />
        <select value={area} onChange={e => setArea(e.target.value)} style={selectStyle}>
          <option value="todas">Todas las áreas</option>
          {areas.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={scoreMin} onChange={e => setScoreMin(e.target.value)} style={selectStyle}>
          <option value="0">Cualquier score</option>
          <option value="60">Score ≥ 60</option>
          <option value="70">Score ≥ 70</option>
          <option value="80">Score ≥ 80</option>
        </select>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : filtrados.length === 0 ? (
        <Card><EmptyState title="Sin resultados" description="Prueba con otros filtros" /></Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 10 }}>
          {filtrados.map((c, i) => {
            const clasif = CLASIFICACION[c.clasificacion_ia] || CLASIFICACION.recomendado
            const skills = parseHabilidades(c.habilidades_detectadas)
            return (
              <motion.div key={c.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
                <Card>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: '50%',
                      background: 'var(--bg-page)', border: '1px solid var(--border)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', flexShrink: 0,
                    }}>{c.nombre[0]}{c.apellidos[0]}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{c.nombre} {c.apellidos}</p>
                      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {c.area?.nombre} · antes: {c.vacante_anterior?.titulo}
                      </p>
                    </div>
                    <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.5px', color: 'var(--text-primary)' }}>{c.score_cv}</span>
                  </div>

                  <Badge variant={clasif.variant}>{clasif.label}</Badge>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, margin: '12px 0' }}>
                    {skills.slice(0, 5).map(s => <Badge key={s}>{s}</Badge>)}
                    {skills.length > 5 && <Badge>+{skills.length - 5}</Badge>}
                  </div>

                  <Button variant="secondary" size="sm" onClick={() => navigate(`/candidatos/${c.id}`)}>
                    Ver perfil
                  </Button>
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}