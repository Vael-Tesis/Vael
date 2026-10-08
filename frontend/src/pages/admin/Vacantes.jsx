import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Button from '../../components/ui/Button.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Card from '../../components/ui/Card.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import Spinner from '../../components/ui/Spinner.jsx'

const ESTADO_VARIANT = {
  abierta:  'success',
  pausada:  'warning',
  cerrada:  'neutral',
  borrador: 'neutral',
}

const PRIORIDAD_VARIANT = {
  urgente: 'danger',
  alta:    'warning',
  media:   'neutral',
  baja:    'neutral',
}

const DEMO_VACANTES = [
  { id: '1', codigo: 'TI-2026-001', titulo: 'Full Stack Developer', estado: 'abierta', prioridad: 'alta', cantidad_posiciones: 2, area: { nombre: 'Tecnología' }, _count: { candidatos: 48 } },
  { id: '2', codigo: 'TI-2026-002', titulo: 'DevOps Engineer',      estado: 'abierta', prioridad: 'urgente', cantidad_posiciones: 1, area: { nombre: 'Tecnología' }, _count: { candidatos: 23 } },
  { id: '3', codigo: 'DIS-2026-001', titulo: 'UX Designer',         estado: 'pausada', prioridad: 'media', cantidad_posiciones: 1, area: { nombre: 'Diseño' }, _count: { candidatos: 15 } },
  { id: '4', codigo: 'COM-2026-001', titulo: 'Sales Executive',     estado: 'borrador', prioridad: 'baja', cantidad_posiciones: 3, area: { nombre: 'Comercial' }, _count: { candidatos: 0 } },
]

export default function Vacantes() {
  const [filtro, setFiltro] = useState('todas')

  const { data, isLoading } = useQuery({
    queryKey: ['vacantes', filtro],
    queryFn: () => api.get('/vacantes', { params: filtro !== 'todas' ? { estado: filtro } : {} })
      .then(r => r.data).catch(() => DEMO_VACANTES),
  })

  const vacantes = data || DEMO_VACANTES
  const navigate = useNavigate()
  const filtradas = filtro === 'todas' ? vacantes : vacantes.filter(v => v.estado === filtro)

  const FILTROS = [
    { key: 'todas', label: 'Todas' },
    { key: 'abierta', label: 'Abiertas' },
    { key: 'pausada', label: 'Pausadas' },
    { key: 'borrador', label: 'Borradores' },
  ]

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Vacantes"
        description="Gestiona las posiciones abiertas de la empresa"
        action={<Button onClick={() => navigate('/vacantes/nueva')}>+ Nueva vacante</Button>}
      />

      {/* Filtros */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {FILTROS.map(f => (
          <button
            key={f.key}
            onClick={() => setFiltro(f.key)}
            style={{
              padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              cursor: 'pointer', transition: 'all 150ms ease',
              border: '1px solid var(--border)',
              background: filtro === f.key ? 'var(--text-primary)' : 'var(--bg-card)',
              color: filtro === f.key ? 'var(--bg-card)' : 'var(--text-secondary)',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Lista */}
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
          <Spinner />
        </div>
      ) : filtradas.length === 0 ? (
        <Card><EmptyState title="Sin vacantes" description="Crea una nueva vacante para comenzar" /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtradas.map((v, i) => (
            <motion.div
              key={v.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <Card style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                      <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                        {v.titulo}
                      </span>
                      <Badge variant={ESTADO_VARIANT[v.estado] || 'neutral'}>{v.estado}</Badge>
                      <Badge variant={PRIORIDAD_VARIANT[v.prioridad] || 'neutral'}>{v.prioridad}</Badge>
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                      <span>{v.codigo}</span>
                      <span>·</span>
                      <span>{v.area?.nombre}</span>
                      <span>·</span>
                      <span>{v.cantidad_posiciones} posición{v.cantidad_posiciones !== 1 ? 'es' : ''}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {v._count?.candidatos ?? 0}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>candidatos</p>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Button variant="secondary" size="sm" onClick={() => navigate(`/vacantes/${v.id}`)}>Ver</Button>
                    <Button variant="ghost" size="sm">···</Button>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}