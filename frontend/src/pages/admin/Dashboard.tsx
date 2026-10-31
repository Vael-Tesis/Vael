import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import { estiloControl } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { ESTADOS_CANDIDATO } from './candidatosComun'
import { ESTADOS as ESTADOS_VACANTE } from './vacantesComun'

/**
 * P-02 Dashboard (HU-20, RF-A-19): cifras del tenant calculadas en el backend
 * (`GET /api/metricas/dashboard`), no en el navegador — el `.jsx` anterior sumaba
 * vacantes y candidatos ya traídos al cliente. `desde`/`hasta` acotan las postulaciones por
 * día y las métricas de decisiones (OE1, M-02); las fotografías de estado actual no cambian.
 */

const ETAPAS_RECOMENDACION: Record<string, string> = { cv: 'CV', examen: 'Examen', entrevista: 'Entrevista' }

function TarjetaMetrica({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <Card>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{etiqueta}</p>
      <p style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.5px', color: 'var(--text-primary)' }}>{valor}</p>
    </Card>
  )
}

function Barra({ valor, maximo }: { valor: number; maximo: number }) {
  const pct = maximo > 0 ? Math.round((valor / maximo) * 100) : 0
  return (
    <div style={{ flex: 1, height: 4, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        style={{ height: '100%', background: 'var(--text-primary)', borderRadius: 999 }}
      />
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  const query = { ...(desde ? { desde } : {}), ...(hasta ? { hasta } : {}) }
  const metricas = useQuery({
    queryKey: ['metricas', 'dashboard', query],
    queryFn: async () => datos(await api.GET('/api/metricas/dashboard', { params: { query } }), 'No se pudo cargar el dashboard'),
  })

  if (metricas.isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
  if (metricas.error || !metricas.data) {
    return <Card><EmptyState title="No se pudo cargar el dashboard" description={mensajeDe(metricas.error, 'Intenta de nuevo')} /></Card>
  }

  const d = metricas.data
  const vacantesActivas = d.vacantes_por_estado.abierta ?? 0
  const totalCandidatos = Object.values(d.candidatos_por_estado).reduce((a, b) => a + b, 0)
  const totalPendientes = Object.values(d.recomendaciones_pendientes_por_etapa).reduce((a, b) => a + b, 0)
  const maxPostulaciones = Math.max(1, ...d.postulaciones_por_dia.map((p) => p.cantidad))
  const candidatosConDatos = Object.entries(d.candidatos_por_estado).filter(([, cantidad]) => cantidad > 0)
  const vacantesConDatos = Object.entries(d.vacantes_por_estado).filter(([, cantidad]) => cantidad > 0)

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader title="Dashboard" description="Resumen del proceso de selección" />

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Desde{' '}
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} style={{ ...estiloControl, height: 30, width: 150 }} />
        </label>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Hasta{' '}
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} style={{ ...estiloControl, height: 30, width: 150 }} />
        </label>
        {(desde || hasta) && (
          <button onClick={() => { setDesde(''); setHasta('') }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 12 }}>
            Limpiar
          </button>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 10, marginBottom: 16 }}>
        <TarjetaMetrica etiqueta="Vacantes abiertas" valor={String(vacantesActivas)} />
        <TarjetaMetrica etiqueta="Candidatos" valor={String(totalCandidatos)} />
        <TarjetaMetrica etiqueta="Recomendaciones pendientes" valor={String(totalPendientes)} />
        <TarjetaMetrica etiqueta="Minutos promedio de revisión (OE1)" valor={d.minutos_promedio_revision != null ? d.minutos_promedio_revision.toFixed(1) : '—'} />
        <TarjetaMetrica etiqueta="Tasa de concordancia (M-02)" valor={d.tasa_concordancia != null ? `${d.tasa_concordancia.toFixed(1)}%` : '—'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <Card>
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 12 }}>Candidatos por estado</p>
          {candidatosConDatos.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin candidatos todavía</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {candidatosConDatos.map(([estado, cantidad]) => (
                <div key={estado} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Badge variant={ESTADOS_CANDIDATO[estado as keyof typeof ESTADOS_CANDIDATO]?.variante ?? 'neutral'}>
                    {ESTADOS_CANDIDATO[estado as keyof typeof ESTADOS_CANDIDATO]?.etiqueta ?? estado}
                  </Badge>
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>{cantidad}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 12 }}>Vacantes por estado</p>
          {vacantesConDatos.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin vacantes todavía</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {vacantesConDatos.map(([estado, cantidad]) => (
                <div key={estado} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Badge variant={ESTADOS_VACANTE[estado as keyof typeof ESTADOS_VACANTE]?.variante ?? 'neutral'}>
                    {ESTADOS_VACANTE[estado as keyof typeof ESTADOS_VACANTE]?.etiqueta ?? estado}
                  </Badge>
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>{cantidad}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>Recomendaciones pendientes por etapa</p>
            <button onClick={() => navigate('/bandeja')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 12 }}>
              Ver bandeja
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {Object.entries(d.recomendaciones_pendientes_por_etapa).map(([etapa, cantidad]) => (
              <div key={etapa} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{ETAPAS_RECOMENDACION[etapa] ?? etapa}</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{cantidad}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 12 }}>Postulaciones por día</p>
          {d.postulaciones_por_dia.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin postulaciones en el rango</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto' }}>
              {d.postulaciones_por_dia.map((p) => (
                <div key={p.fecha} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', width: 80, flexShrink: 0 }}>{p.fecha}</span>
                  <Barra valor={p.cantidad} maximo={maxPostulaciones} />
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', width: 24, textAlign: 'right' }}>{p.cantidad}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
