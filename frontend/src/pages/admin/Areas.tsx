import { useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import { usuarioActual } from '../../auth/sesion'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'

/**
 * P-17 Áreas (HU-05, RF-A-04): admin y gerente crean, editan, activan y desactivan áreas;
 * el código corto es único en la empresa; solo el admin elimina, y solo un área sin vacantes.
 */

type Area = Esquemas['AreaResponse']

interface FormularioArea {
  nombre: string
  codigo_corto: string
  descripcion: string
  instruccion_ia: string
}

const VACIO: FormularioArea = { nombre: '', codigo_corto: '', descripcion: '', instruccion_ia: '' }

const estiloInput: CSSProperties = {
  height: 34, padding: '0 10px', border: '1px solid var(--border)', borderRadius: 6,
  background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: 13, outline: 'none', width: '100%',
}

function Editor({ inicial, area, onCerrar }: { inicial: FormularioArea; area?: Area; onCerrar: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(inicial)
  const valido = form.nombre.trim() !== '' && form.codigo_corto.trim() !== ''

  const guardar = useMutation({
    mutationFn: async () => {
      const cuerpo = {
        nombre: form.nombre.trim(),
        codigo_corto: form.codigo_corto.trim().toUpperCase(),
        descripcion: form.descripcion.trim() || null,
        instruccion_ia: form.instruccion_ia.trim() || null,
      }
      return area
        ? datos(await api.PUT('/api/areas/{area_id}', { params: { path: { area_id: area.id } }, body: cuerpo }))
        : datos(await api.POST('/api/areas', { body: cuerpo }))
    },
    onSuccess: () => {
      toast.success(area ? 'Área actualizada' : 'Área creada')
      queryClient.invalidateQueries({ queryKey: ['areas'] })
      onCerrar()
    },
    onError: (error) => toast.error(mensajeDe(error, 'No se pudo guardar el área')),
  })

  const campo = (clave: keyof FormularioArea) => ({
    value: form[clave],
    onChange: (e: { target: { value: string } }) => setForm((f) => ({ ...f, [clave]: e.target.value })),
  })

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 16 }}>
      <Card>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 14 }}>
          {area ? `Editar ${area.nombre}` : 'Nueva área'}
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, marginBottom: 10 }}>
          <input style={estiloInput} placeholder="Nombre del área" aria-label="Nombre del área" {...campo('nombre')} />
          <input style={estiloInput} placeholder="Código corto (ej: TI)" aria-label="Código corto" maxLength={10} {...campo('codigo_corto')} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
          <input style={estiloInput} placeholder="Descripción (opcional)" aria-label="Descripción" {...campo('descripcion')} />
          <input
            style={estiloInput}
            placeholder="Instrucción para la IA al evaluar CVs (opcional)"
            aria-label="Instrucción para la IA"
            {...campo('instruccion_ia')}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
          <Button variant="secondary" onClick={onCerrar}>Cancelar</Button>
          <Button onClick={() => guardar.mutate()} disabled={!valido || guardar.isPending}>
            {guardar.isPending ? 'Guardando...' : area ? 'Guardar cambios' : 'Crear área'}
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

export default function Areas() {
  const queryClient = useQueryClient()
  const esAdmin = usuarioActual()?.rol === 'admin'
  const [editando, setEditando] = useState<Area | 'nueva' | null>(null)
  const [porEliminar, setPorEliminar] = useState<Area | null>(null)

  const { data: areas, isLoading, error } = useQuery({
    queryKey: ['areas'],
    queryFn: async () => datos(await api.GET('/api/areas'), 'No se pudieron cargar las áreas'),
  })

  const cambiarEstado = useMutation({
    mutationFn: async (area: Area) => {
      const opciones = { params: { path: { area_id: area.id } } }
      return datos(
        area.activa
          ? await api.POST('/api/areas/{area_id}/desactivar', opciones)
          : await api.POST('/api/areas/{area_id}/activar', opciones),
      )
    },
    onSuccess: (area) => {
      toast.success(area.activa ? 'Área activada' : 'Área desactivada')
      queryClient.invalidateQueries({ queryKey: ['areas'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo cambiar el estado del área')),
  })

  const eliminar = useMutation({
    mutationFn: async (area: Area) =>
      datos(await api.DELETE('/api/areas/{area_id}', { params: { path: { area_id: area.id } } })),
    onSuccess: () => {
      toast.success('Área eliminada')
      queryClient.invalidateQueries({ queryKey: ['areas'] })
      setPorEliminar(null)
    },
    onError: (e) => {
      toast.error(mensajeDe(e, 'No se pudo eliminar el área'))
      setPorEliminar(null)
    },
  })

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Áreas"
        description="Áreas de la empresa y la instrucción que usa la IA al evaluar sus CVs"
        action={editando === null && <Button onClick={() => setEditando('nueva')}>+ Nueva área</Button>}
      />

      {editando !== null && (
        <Editor
          key={editando === 'nueva' ? 'nueva' : editando.id}
          area={editando === 'nueva' ? undefined : editando}
          inicial={
            editando === 'nueva'
              ? VACIO
              : {
                  nombre: editando.nombre,
                  codigo_corto: editando.codigo_corto,
                  descripcion: editando.descripcion ?? '',
                  instruccion_ia: editando.instruccion_ia ?? '',
                }
          }
          onCerrar={() => setEditando(null)}
        />
      )}

      {isLoading && <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner /></div>}
      {error && <EmptyState title="No se pudieron cargar las áreas" description={mensajeDe(error, 'Intenta de nuevo')} />}
      {areas && areas.length === 0 && <EmptyState title="Aún no hay áreas" description="Crea la primera para organizar tus vacantes" />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
        {areas?.map((area, i) => (
          <motion.div key={area.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{
                  minWidth: 36, height: 36, padding: '0 6px', borderRadius: 8, background: 'var(--brand-soft)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, color: 'var(--brand)',
                }}>
                  {area.codigo_corto}
                </div>
                <Badge variant={area.activa ? 'success' : 'neutral'}>{area.activa ? 'Activa' : 'Inactiva'}</Badge>
              </div>
              <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>{area.nombre}</p>
              {area.descripcion && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>{area.descripcion}</p>}
              {area.instruccion_ia && (
                <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>IA: {area.instruccion_ia}</p>
              )}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
                <Button size="sm" variant="secondary" onClick={() => setEditando(area)}>Editar</Button>
                <Button size="sm" variant="ghost" onClick={() => cambiarEstado.mutate(area)} disabled={cambiarEstado.isPending}>
                  {area.activa ? 'Desactivar' : 'Activar'}
                </Button>
                {esAdmin && (
                  <Button size="sm" variant="ghost" onClick={() => setPorEliminar(area)}>Eliminar</Button>
                )}
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      <ConfirmModal
        abierto={porEliminar !== null}
        titulo={`¿Eliminar el área ${porEliminar?.nombre ?? ''}?`}
        textoConfirmar="Eliminar"
        peligroso
        procesando={eliminar.isPending}
        onConfirmar={() => porEliminar && eliminar.mutate(porEliminar)}
        onCancelar={() => setPorEliminar(null)}
      >
        Solo se puede eliminar un área sin vacantes. Si tiene vacantes, desactívala.
      </ConfirmModal>
    </div>
  )
}
