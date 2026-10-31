import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import { estiloControl } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { CLASIFICACIONES } from './candidatosComun'

/**
 * P-18 Banco de talento (HU-14, RF-A-17): candidatos que RRHH marcó explícitamente como
 * disponibles para procesos futuros (`GET /candidatos/banco-talento`, filtro por área en el
 * backend); la acción "Enviar al banco" vive en el detalle del candidato (V-11).
 */

export default function BancoTalento() {
  const navigate = useNavigate()
  const [busqueda, setBusqueda] = useState('')
  const [scoreMin, setScoreMin] = useState('0')
  const [areaId, setAreaId] = useState('')

  const areas = useQuery({ queryKey: ['areas'], queryFn: async () => datos(await api.GET('/api/areas')) })
  const vacantes = useQuery({ queryKey: ['vacantes', 'todas'], queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })) })
  const banco = useQuery({
    queryKey: ['banco-talento', areaId],
    queryFn: async () =>
      datos(await api.GET('/api/candidatos/banco-talento', { params: { query: areaId ? { area_id: areaId } : {} } }), 'No se pudo cargar el banco de talento'),
  })

  const vacantePorId = new Map((vacantes.data ?? []).map((v) => [v.id, v]))
  const areaPorId = new Map((areas.data ?? []).map((a) => [a.id, a.nombre]))

  const filtrados = (banco.data ?? []).filter((c) => {
    const texto = `${c.nombre} ${c.apellidos} ${c.habilidades_detectadas.join(' ')}`.toLowerCase()
    return texto.includes(busqueda.toLowerCase()) && (c.score_cv ?? 0) >= Number(scoreMin)
  })

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader title="Banco de talento" description="Candidatos marcados por RRHH como disponibles para futuras vacantes" />

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre o habilidad..."
          style={{ ...estiloControl, width: 280 }}
        />
        <select value={areaId} onChange={(e) => setAreaId(e.target.value)} style={estiloControl}>
          <option value="">Todas las áreas</option>
          {(areas.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
        </select>
        <select value={scoreMin} onChange={(e) => setScoreMin(e.target.value)} style={estiloControl}>
          <option value="0">Cualquier score</option>
          <option value="60">Score ≥ 60</option>
          <option value="70">Score ≥ 70</option>
          <option value="80">Score ≥ 80</option>
        </select>
      </div>

      {banco.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : banco.error ? (
        <Card><EmptyState title="No se pudo cargar el banco de talento" description={mensajeDe(banco.error, 'Intenta de nuevo')} /></Card>
      ) : filtrados.length === 0 ? (
        <Card><EmptyState title="Sin resultados" description="Prueba con otros filtros, o envía candidatos al banco desde su detalle" /></Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 10 }}>
          {filtrados.map((c, i) => {
            const vacante = vacantePorId.get(c.vacante_id)
            const area = vacante ? areaPorId.get(vacante.area_id) : undefined
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
                        {area ?? 'Área'} · antes: {vacante?.titulo ?? 'Vacante'}
                      </p>
                    </div>
                    <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.5px', color: 'var(--text-primary)' }}>{c.score_cv ?? '—'}</span>
                  </div>

                  {c.clasificacion_ia && <Badge variant={CLASIFICACIONES[c.clasificacion_ia].variante}>{CLASIFICACIONES[c.clasificacion_ia].etiqueta}</Badge>}

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, margin: '12px 0' }}>
                    {c.habilidades_detectadas.slice(0, 5).map((s) => <Badge key={s}>{s}</Badge>)}
                    {c.habilidades_detectadas.length > 5 && <Badge>+{c.habilidades_detectadas.length - 5}</Badge>}
                  </div>

                  <Button variant="secondary" size="sm" onClick={() => navigate(`/candidatos/${c.id}`)}>Ver perfil</Button>
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
