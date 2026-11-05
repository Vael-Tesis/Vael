import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import { Filtros, Selector, type Opcion } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { SEMAFORO, type Semaforo, nombreCompleto, useCandidatos, useVacantes, varianteEstadoExamen } from './evaluacionesComun'

/** P-11 Exámenes (HU-19, RF-A-16): resultados y semáforo de integridad de cada evaluación. */

type FiltroSemaforo = 'todos' | Semaforo
const FILTROS: readonly Opcion<FiltroSemaforo>[] = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'verde', etiqueta: '● Verde' },
  { valor: 'amarillo', etiqueta: '● Amarillo' },
  { valor: 'rojo', etiqueta: '● Rojo' },
]

export default function Examenes() {
  const navigate = useNavigate()
  const [semaforo, setSemaforo] = useState<FiltroSemaforo>('todos')
  const [vacanteId, setVacanteId] = useState('')

  const query = vacanteId ? { vacante_id: vacanteId } : {}
  const examenes = useQuery({
    queryKey: ['examenes', query],
    queryFn: async () => datos(await api.GET('/api/evaluaciones/examenes', { params: { query } }), 'No se pudieron cargar los exámenes'),
  })
  const candidatos = useCandidatos()
  const vacantes = useVacantes()

  const candidatoPorId = new Map((candidatos.data ?? []).map((c) => [c.id, c]))
  const tituloVacante = new Map((vacantes.data ?? []).map((v) => [v.id, v.titulo]))

  const filtrados = (examenes.data ?? []).filter((e) => semaforo === 'todos' || e.semaforo === semaforo)

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader title="Exámenes" description="Resultados y estado de integridad de cada evaluación" />

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start', marginBottom: 4 }}>
        <Filtros actual={semaforo} opciones={FILTROS} onCambio={setSemaforo} />
        <div style={{ minWidth: 220, flex: '0 1 300px' }}>
          <Selector
            valor={vacanteId}
            onCambio={setVacanteId}
            opciones={[{ valor: '', etiqueta: 'Todas las vacantes' }, ...(vacantes.data ?? []).map((v) => ({ valor: v.id, etiqueta: v.titulo }))]}
          />
        </div>
      </div>

      <Card padding="0">
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 160px 80px 100px 110px 70px', padding: '8px 16px',
          borderBottom: '1px solid var(--border)', fontSize: 11, fontWeight: 500,
          color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', gap: 12,
        }}>
          <span>Candidato</span>
          <span>Vacante</span>
          <span style={{ textAlign: 'center' }}>Nota</span>
          <span>Integridad</span>
          <span>Estado</span>
          <span />
        </div>

        {examenes.isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
        ) : examenes.error ? (
          <EmptyState title="No se pudieron cargar los exámenes" description={mensajeDe(examenes.error, 'Intenta de nuevo')} />
        ) : filtrados.length === 0 ? (
          <EmptyState title="Sin exámenes" />
        ) : (
          filtrados.map((e, i) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
              onClick={() => navigate(`/examenes/${e.id}`)}
              style={{
                display: 'grid', gridTemplateColumns: '1fr 160px 80px 100px 110px 70px', padding: '11px 16px',
                borderBottom: '1px solid var(--border)', alignItems: 'center', gap: 12, cursor: 'pointer',
              }}
            >
              <div>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{nombreCompleto(candidatoPorId.get(e.candidato_id))}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Riesgo: {e.puntaje_riesgo} pts</p>
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{tituloVacante.get(e.vacante_id) ?? 'Vacante'}</span>
              <div style={{ textAlign: 'center' }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: e.nota != null ? (e.nota >= 13 ? 'var(--success-text)' : 'var(--danger-text)') : 'var(--text-muted)' }}>
                  {e.nota != null ? `${e.nota}/20` : '—'}
                </span>
              </div>
              <Badge variant={SEMAFORO[e.semaforo].variante}>● {SEMAFORO[e.semaforo].etiqueta}</Badge>
              <Badge variant={varianteEstadoExamen(e.estado)}>{e.estado.replace('_', ' ')}</Badge>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Ver</span>
            </motion.div>
          ))
        )}
      </Card>
    </div>
  )
}
