import { useState, type CSSProperties } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'

/**
 * P-16 Plantillas de evaluación (HU-06, RF-A-05): crear y editar plantillas con sus
 * dimensiones; si los pesos no suman 100, el backend las rechaza con un mensaje claro y la
 * pantalla lo avisa antes de enviar. Ruta corregida: /api/plantillas (DEC-008).
 */

type Plantilla = Esquemas['PlantillaDetalleResponse']

interface DimensionEditable {
  nombre: string
  descripcion: string
  peso: string
  puntaje_maximo: number
}

const PUNTAJE_MAXIMO = 20  // doc 05: cada dimensión se califica sobre 20

interface FormularioPlantilla {
  nombre: string
  descripcion: string
  activa: boolean
  dimensiones: DimensionEditable[]
}

const NUEVA: FormularioPlantilla = {
  nombre: '',
  descripcion: '',
  activa: true,
  dimensiones: [
    { nombre: '', descripcion: '', peso: '50', puntaje_maximo: PUNTAJE_MAXIMO },
    { nombre: '', descripcion: '', peso: '50', puntaje_maximo: PUNTAJE_MAXIMO },
  ],
}

const estiloInput: CSSProperties = {
  height: 34, padding: '0 10px', border: '1px solid var(--border)', borderRadius: 6,
  background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: 13, outline: 'none', minWidth: 0,
}

function desdePlantilla(p: Plantilla): FormularioPlantilla {
  return {
    nombre: p.nombre,
    descripcion: p.descripcion ?? '',
    activa: p.activa,
    dimensiones: p.dimensiones.map((d) => ({
      nombre: d.nombre, descripcion: d.descripcion ?? '', peso: String(d.peso), puntaje_maximo: d.puntaje_maximo,
    })),
  }
}

function Editor({ plantilla, onCerrar }: { plantilla?: Plantilla; onCerrar: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<FormularioPlantilla>(plantilla ? desdePlantilla(plantilla) : NUEVA)

  const total = form.dimensiones.reduce((suma, d) => suma + (Number(d.peso) || 0), 0)
  const sumaCorrecta = Math.abs(total - 100) < 0.01
  const valido =
    form.nombre.trim() !== '' && sumaCorrecta && form.dimensiones.every((d) => d.nombre.trim() !== '' && Number(d.peso) > 0)

  const guardar = useMutation({
    mutationFn: async () => {
      const dimensiones = form.dimensiones.map((d) => ({
        nombre: d.nombre.trim(),
        descripcion: d.descripcion.trim() || null,
        peso: Number(d.peso),
        puntaje_maximo: d.puntaje_maximo,
      }))
      const base = { nombre: form.nombre.trim(), descripcion: form.descripcion.trim() || null, activa: form.activa, dimensiones }
      return plantilla
        ? datos(await api.PUT('/api/plantillas/{plantilla_id}', { params: { path: { plantilla_id: plantilla.id } }, body: base }))
        : datos(await api.POST('/api/plantillas', { body: base }))
    },
    onSuccess: () => {
      toast.success(plantilla ? 'Plantilla actualizada' : 'Plantilla creada')
      queryClient.invalidateQueries({ queryKey: ['plantillas'] })
      onCerrar()
    },
    onError: (error) => toast.error(mensajeDe(error, 'No se pudo guardar la plantilla')),
  })

  const cambiarDimension = (indice: number, campo: 'nombre' | 'descripcion' | 'peso', valor: string) =>
    setForm((f) => ({ ...f, dimensiones: f.dimensiones.map((d, j) => (j === indice ? { ...d, [campo]: valor } : d)) }))

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 16 }}>
      <Card>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 14 }}>
          {plantilla ? `Editar ${plantilla.nombre}` : 'Nueva plantilla'}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: 12 }}>
          <input style={estiloInput} placeholder="Nombre de la plantilla" aria-label="Nombre de la plantilla" value={form.nombre}
            onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))} />
          <input style={estiloInput} placeholder="Descripción (opcional)" aria-label="Descripción" value={form.descripcion}
            onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))} />
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
          <input type="checkbox" checked={form.activa} onChange={(e) => setForm((f) => ({ ...f, activa: e.target.checked }))} />
          Activa (EVA la usa en las entrevistas)
        </label>

        <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
          Dimensiones a evaluar
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
          {form.dimensiones.map((d, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input style={{ ...estiloInput, flex: '2 1 160px' }} placeholder="Nombre de la dimensión" aria-label={`Dimensión ${i + 1}`}
                value={d.nombre} onChange={(e) => cambiarDimension(i, 'nombre', e.target.value)} />
              <input style={{ ...estiloInput, flex: '3 1 200px' }} placeholder="Qué observa (opcional)" aria-label={`Descripción de la dimensión ${i + 1}`}
                value={d.descripcion} onChange={(e) => cambiarDimension(i, 'descripcion', e.target.value)} />
              <input style={{ ...estiloInput, width: 72 }} type="number" min="1" max="100" aria-label={`Peso de la dimensión ${i + 1}`}
                value={d.peso} onChange={(e) => cambiarDimension(i, 'peso', e.target.value)} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>%</span>
              <button
                type="button"
                aria-label={`Quitar la dimensión ${i + 1}`}
                onClick={() => setForm((f) => ({ ...f, dimensiones: f.dimensiones.filter((_, j) => j !== i) }))}
                disabled={form.dimensiones.length <= 1}
                style={{
                  background: 'none', border: 'none', fontSize: 16, color: 'var(--text-muted)',
                  cursor: form.dimensiones.length <= 1 ? 'not-allowed' : 'pointer', opacity: form.dimensiones.length <= 1 ? 0.4 : 1,
                }}
              >×</button>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <Button variant="ghost" size="sm"
            onClick={() => setForm((f) => ({ ...f, dimensiones: [...f.dimensiones, { nombre: '', descripcion: '', peso: '0', puntaje_maximo: PUNTAJE_MAXIMO }] }))}>
            + Agregar dimensión
          </Button>
          <Badge variant={sumaCorrecta ? 'success' : 'danger'}>
            Total: {total}% {!sumaCorrecta && '(debe sumar 100%)'}
          </Badge>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
          <Button variant="secondary" onClick={onCerrar}>Cancelar</Button>
          <Button onClick={() => guardar.mutate()} disabled={!valido || guardar.isPending}>
            {guardar.isPending ? 'Guardando...' : plantilla ? 'Guardar cambios' : 'Crear plantilla'}
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

export default function Plantillas() {
  const [editando, setEditando] = useState<Plantilla | 'nueva' | null>(null)

  const listado = useQuery({
    queryKey: ['plantillas'],
    queryFn: async () => datos(await api.GET('/api/plantillas'), 'No se pudieron cargar las plantillas'),
  })

  // El listado no trae las dimensiones: se pide el detalle de cada plantilla
  const detalles = useQueries({
    queries: (listado.data ?? []).map((p) => ({
      queryKey: ['plantillas', p.id],
      queryFn: async () =>
        datos(await api.GET('/api/plantillas/{plantilla_id}', { params: { path: { plantilla_id: p.id } } })),
    })),
  })
  const plantillas = detalles.map((d) => d.data).filter((p): p is Plantilla => p !== undefined)

  return (
    <div style={{ padding: '20px 24px', maxWidth: 960 }}>
      <PageHeader
        title="Plantillas de evaluación"
        description="Dimensiones y pesos con los que EVA evalúa cada entrevista"
        action={editando === null && <Button onClick={() => setEditando('nueva')}>+ Nueva plantilla</Button>}
      />

      {editando !== null && (
        <Editor
          key={editando === 'nueva' ? 'nueva' : editando.id}
          plantilla={editando === 'nueva' ? undefined : editando}
          onCerrar={() => setEditando(null)}
        />
      )}

      {listado.isLoading && <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner /></div>}
      {listado.error && <EmptyState title="No se pudieron cargar las plantillas" description={mensajeDe(listado.error, 'Intenta de nuevo')} />}
      {listado.data?.length === 0 && <EmptyState title="Aún no hay plantillas" description="Crea una para que EVA sepa qué evaluar" />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 10 }}>
        {plantillas.map((p, i) => (
          <motion.div key={p.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 14 }}>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{p.nombre}</p>
                  {p.descripcion && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{p.descripcion}</p>}
                </div>
                <Badge variant={p.activa ? 'success' : 'neutral'}>{p.activa ? 'Activa' : 'Inactiva'}</Badge>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {p.dimensiones.map((d) => (
                  <div key={d.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{d.nombre}</span>
                      <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{d.peso}%</span>
                    </div>
                    <div style={{ height: 3, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden' }}>
                      <motion.div
                        initial={{ width: 0 }} animate={{ width: `${d.peso}%` }} transition={{ duration: 0.5, ease: 'easeOut' }}
                        style={{ height: '100%', background: 'var(--brand)', borderRadius: 999 }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 14, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
                <Button size="sm" variant="secondary" onClick={() => setEditando(p)}>Editar</Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
