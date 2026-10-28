import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { Iniciales, PuntajeCv } from '../../components/ui/Candidato'
import EmptyState from '../../components/ui/EmptyState'
import { Selector, estiloControl, type Opcion } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { CLASIFICACIONES, ESTADOS_CANDIDATO, type Candidato, type EstadoCandidato } from './candidatosComun'

/**
 * P-06 Candidatos (HU-11, HU-12, HU-13): filtros por vacante, estado y etiqueta; muestra los
 * estados por confirmar (DEC-009) y permite volver a analizar el CV.
 */

const TODOS = ''

const OPCIONES_ESTADO: Opcion<EstadoCandidato | typeof TODOS>[] = [
  { valor: TODOS, etiqueta: 'Todos los estados' },
  ...(Object.entries(ESTADOS_CANDIDATO) as [EstadoCandidato, { etiqueta: string }][]).map(([valor, { etiqueta }]) => ({ valor, etiqueta })),
]

export default function Candidatos() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [busqueda, setBusqueda] = useState('')
  const [vacanteId, setVacanteId] = useState(TODOS)
  const [estado, setEstado] = useState<EstadoCandidato | typeof TODOS>(TODOS)
  const [tagId, setTagId] = useState(TODOS)

  const filtros = {
    ...(vacanteId ? { vacante_id: vacanteId } : {}),
    ...(estado ? { estado } : {}),
    ...(tagId ? { tag_id: tagId } : {}),
  }
  const candidatos = useQuery({
    queryKey: ['candidatos', filtros],
    queryFn: async () => datos(await api.GET('/api/candidatos', { params: { query: filtros } }), 'No se pudieron cargar los candidatos'),
  })
  const vacantes = useQuery({ queryKey: ['vacantes', 'todas'], queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })) })
  const tags = useQuery({ queryKey: ['tags'], queryFn: async () => datos(await api.GET('/api/tags')) })
  const tituloVacante = new Map((vacantes.data ?? []).map((v) => [v.id, v.titulo]))

  const analizar = useMutation({
    mutationFn: async (c: Candidato) =>
      datos(await api.POST('/api/candidatos/{candidato_id}/analizar', { params: { path: { candidato_id: c.id } } })),
    onSuccess: () => {
      toast.success('Análisis de CV en curso')
      queryClient.invalidateQueries({ queryKey: ['candidatos'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo iniciar el análisis')),
  })

  const texto = busqueda.trim().toLowerCase()
  const visibles = (candidatos.data ?? []).filter((c) => `${c.nombre} ${c.apellidos} ${c.email}`.toLowerCase().includes(texto))

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Candidatos"
        description="Postulantes de todas las vacantes"
        action={
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Button variant="secondary" onClick={() => navigate('/bandeja')}>Bandeja de recomendaciones</Button>
            <Button onClick={() => navigate('/candidatos/registrar')}>+ Agregar candidatos</Button>
          </div>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8, marginBottom: 16 }}>
        <input style={estiloControl} placeholder="Buscar por nombre o correo" aria-label="Buscar" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        <Selector valor={vacanteId} onCambio={setVacanteId}
          opciones={[{ valor: TODOS, etiqueta: 'Todas las vacantes' }, ...(vacantes.data ?? []).map((v) => ({ valor: v.id, etiqueta: v.titulo }))]} />
        <Selector valor={estado} onCambio={setEstado} opciones={OPCIONES_ESTADO} />
        <Selector valor={tagId} onCambio={setTagId}
          opciones={[{ valor: TODOS, etiqueta: 'Todas las etiquetas' }, ...(tags.data ?? []).map((t) => ({ valor: t.id, etiqueta: t.nombre }))]} />
      </div>

      {candidatos.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : candidatos.error ? (
        <Card><EmptyState title="No se pudieron cargar los candidatos" description={mensajeDe(candidatos.error, 'Intenta de nuevo')} /></Card>
      ) : visibles.length === 0 ? (
        <Card><EmptyState title="Sin candidatos" description="Registra candidatos o ajusta los filtros" /></Card>
      ) : (
        <Card padding="0">
          {visibles.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: Math.min(i, 10) * 0.02 }}
              style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', flexWrap: 'wrap', borderBottom: i < visibles.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <Iniciales nombre={c.nombre} apellidos={c.apellidos} />
              <div style={{ flex: '1 1 200px', minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{c.nombre} {c.apellidos}</p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.email} · {tituloVacante.get(c.vacante_id) ?? 'Vacante'}
                </p>
              </div>
              <Badge variant={ESTADOS_CANDIDATO[c.estado].variante}>{ESTADOS_CANDIDATO[c.estado].etiqueta}</Badge>
              {c.clasificacion_ia && <Badge variant={CLASIFICACIONES[c.clasificacion_ia].variante}>{CLASIFICACIONES[c.clasificacion_ia].etiqueta}</Badge>}
              <PuntajeCv valor={c.score_cv} />
              <div style={{ display: 'flex', gap: 6 }}>
                {(c.estado === 'postulado' || c.estado === 'cv_por_confirmar') && (
                  <Button variant="ghost" size="sm" onClick={() => analizar.mutate(c)} disabled={analizar.isPending}>
                    {c.estado === 'postulado' ? 'Analizar' : 'Reanalizar'}
                  </Button>
                )}
                <Button variant="secondary" size="sm" onClick={() => navigate(`/candidatos/${c.id}`)}>Ver</Button>
              </div>
            </motion.div>
          ))}
        </Card>
      )}
    </div>
  )
}
