import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import { Filtros, type Opcion } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { ESTADOS, PRIORIDADES, type EstadoVacante, type Vacante } from './vacantesComun'

/** P-03 Vacantes (HU-08): listado con filtro por estado; duplicar y eliminar (solo en borrador). */

type Filtro = EstadoVacante | 'todas'

const FILTROS: readonly Opcion<Filtro>[] = [
  { valor: 'todas', etiqueta: 'Todas' },
  { valor: 'abierta', etiqueta: 'Abiertas' },
  { valor: 'pausada', etiqueta: 'Pausadas' },
  { valor: 'borrador', etiqueta: 'Borradores' },
  { valor: 'cerrada', etiqueta: 'Cerradas' },
]

export default function Vacantes() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filtro, setFiltro] = useState<Filtro>('todas')
  const [porEliminar, setPorEliminar] = useState<Vacante | null>(null)

  const vacantes = useQuery({
    queryKey: ['vacantes', filtro],
    queryFn: async () =>
      datos(
        await api.GET('/api/vacantes', { params: { query: filtro === 'todas' ? {} : { estado: filtro } } }),
        'No se pudieron cargar las vacantes',
      ),
  })
  const areas = useQuery({ queryKey: ['areas'], queryFn: async () => datos(await api.GET('/api/areas')) })
  const nombreArea = new Map((areas.data ?? []).map((a) => [a.id, a.nombre]))

  const duplicar = useMutation({
    mutationFn: async (vacante: Vacante) =>
      datos(await api.POST('/api/vacantes/{vacante_id}/duplicar', { params: { path: { vacante_id: vacante.id } } })),
    onSuccess: (copia) => {
      toast.success(`Copia creada en borrador: ${copia.codigo}`)
      queryClient.invalidateQueries({ queryKey: ['vacantes'] })
      navigate(`/vacantes/${copia.id}`)
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo duplicar la vacante')),
  })

  const eliminar = useMutation({
    mutationFn: async (vacante: Vacante) =>
      datos(await api.DELETE('/api/vacantes/{vacante_id}', { params: { path: { vacante_id: vacante.id } } })),
    onSuccess: () => {
      toast.success('Vacante eliminada')
      queryClient.invalidateQueries({ queryKey: ['vacantes'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo eliminar la vacante')),
    onSettled: () => setPorEliminar(null),
  })

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Vacantes"
        description="Gestiona las posiciones de la empresa"
        action={<Button onClick={() => navigate('/vacantes/nueva')}>+ Nueva vacante</Button>}
      />

      <Filtros actual={filtro} opciones={FILTROS} onCambio={setFiltro} />

      {vacantes.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : vacantes.error ? (
        <Card><EmptyState title="No se pudieron cargar las vacantes" description={mensajeDe(vacantes.error, 'Intenta de nuevo')} /></Card>
      ) : vacantes.data?.length === 0 ? (
        <Card><EmptyState title="Sin vacantes" description="Crea una nueva vacante para comenzar" /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {vacantes.data?.map((v, i) => (
            <motion.div key={v.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
              <Card style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ flex: '1 1 260px', minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{v.titulo}</span>
                      <Badge variant={ESTADOS[v.estado].variante}>{ESTADOS[v.estado].etiqueta}</Badge>
                      <Badge variant={PRIORIDADES[v.prioridad].variante}>{PRIORIDADES[v.prioridad].etiqueta}</Badge>
                      {v.confidencial && <Badge variant="info">Confidencial</Badge>}
                    </div>
                    <div style={{ display: 'flex', gap: 8, fontSize: 12, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                      <span>{v.codigo}</span>
                      {nombreArea.has(v.area_id) && <><span>·</span><span>{nombreArea.get(v.area_id)}</span></>}
                      <span>·</span>
                      <span>{v.cantidad_posiciones} {v.cantidad_posiciones === 1 ? 'posición' : 'posiciones'}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Button variant="secondary" size="sm" onClick={() => navigate(`/vacantes/${v.id}`)}>Ver</Button>
                    <Button variant="ghost" size="sm" onClick={() => duplicar.mutate(v)} disabled={duplicar.isPending}>Duplicar</Button>
                    {v.estado === 'borrador' && (
                      <Button variant="ghost" size="sm" onClick={() => setPorEliminar(v)}>Eliminar</Button>
                    )}
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      <ConfirmModal
        abierto={porEliminar !== null}
        titulo={`¿Eliminar ${porEliminar?.titulo ?? ''}?`}
        textoConfirmar="Eliminar"
        peligroso
        procesando={eliminar.isPending}
        onConfirmar={() => porEliminar && eliminar.mutate(porEliminar)}
        onCancelar={() => setPorEliminar(null)}
      >
        Solo se eliminan vacantes en borrador. Esta acción no se puede deshacer.
      </ConfirmModal>
    </div>
  )
}
