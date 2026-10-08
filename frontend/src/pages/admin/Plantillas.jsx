import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Button from '../../components/ui/Button.jsx'

const DEMO = [
  { id: '1', nombre: 'Técnico Estándar', descripcion: 'Para perfiles de TI y áreas técnicas', activa: true, dimensiones: [
    { nombre: 'Claridad de expresión', peso: 20 }, { nombre: 'Coherencia de respuestas', peso: 20 },
    { nombre: 'Precisión técnica', peso: 30 }, { nombre: 'Comunicación efectiva', peso: 20 },
    { nombre: 'Seguridad y confianza', peso: 10 },
  ]},
  { id: '2', nombre: 'Comercial', descripcion: 'Ventas y atención al cliente', activa: true, dimensiones: [
    { nombre: 'Persuasión', peso: 30 }, { nombre: 'Escucha activa', peso: 20 },
    { nombre: 'Orientación a resultados', peso: 25 }, { nombre: 'Manejo de objeciones', peso: 25 },
  ]},
  { id: '3', nombre: 'Liderazgo', descripcion: 'Jefaturas y gerencias', activa: true, dimensiones: [
    { nombre: 'Visión estratégica', peso: 25 }, { nombre: 'Gestión de equipos', peso: 25 },
    { nombre: 'Toma de decisiones', peso: 25 }, { nombre: 'Comunicación ejecutiva', peso: 25 },
  ]},
  { id: '4', nombre: 'Creativo', descripcion: 'Diseño y contenidos', activa: true, dimensiones: [
    { nombre: 'Originalidad', peso: 30 }, { nombre: 'Pensamiento divergente', peso: 25 },
    { nombre: 'Argumentación de ideas', peso: 25 }, { nombre: 'Adaptabilidad', peso: 20 },
  ]},
]

const inputStyle = {
  height: 34, padding: '0 10px', border: '1px solid var(--border)',
  borderRadius: 6, background: 'var(--bg-card)', color: 'var(--text-primary)',
  fontSize: 13, outline: 'none',
}

function Editor({ onCancel, onSaved }) {
  const [form, setForm] = useState({
    nombre: '', descripcion: '',
    dimensiones: [{ nombre: '', peso: 50 }, { nombre: '', peso: 50 }],
  })
  const [guardando, setGuardando] = useState(false)

  const total = form.dimensiones.reduce((s, d) => s + (Number(d.peso) || 0), 0)
  const valido = form.nombre.trim() && total === 100 && form.dimensiones.every(d => d.nombre.trim())

  const setDim = (i, campo, valor) =>
    setForm(f => ({ ...f, dimensiones: f.dimensiones.map((d, j) => j === i ? { ...d, [campo]: valor } : d) }))
  const addDim = () =>
    setForm(f => ({ ...f, dimensiones: [...f.dimensiones, { nombre: '', peso: 0 }] }))
  const removeDim = (i) =>
    setForm(f => ({ ...f, dimensiones: f.dimensiones.filter((_, j) => j !== i) }))

  async function guardar() {
    setGuardando(true)
    const payload = {
      ...form,
      dimensiones: form.dimensiones.map(d => ({ ...d, peso: Number(d.peso) })),
    }
    try {
      const { data } = await api.post('/entrevista/plantillas', payload)
      onSaved(data)
      toast.success('Plantilla creada')
    } catch (err) {
      if (sinBackend(err)) {
        onSaved({ id: String(Date.now()), activa: true, ...payload })
        toast.success('Plantilla creada (modo desarrollo)')
      } else {
        toast.error(err.response?.data?.detail || 'No se pudo crear la plantilla')
      }
    } finally {
      setGuardando(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 16 }}>
      <Card>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 14 }}>Nueva plantilla</p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
          <input style={inputStyle} placeholder="Nombre de la plantilla" value={form.nombre}
            onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} />
          <input style={inputStyle} placeholder="Descripción (opcional)" value={form.descripcion}
            onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))} />
        </div>

        <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
          Dimensiones a evaluar
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
          {form.dimensiones.map((d, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input style={{ ...inputStyle, flex: 1 }} placeholder="Nombre de la dimensión" value={d.nombre}
                onChange={e => setDim(i, 'nombre', e.target.value)} />
              <input style={{ ...inputStyle, width: 70 }} type="number" min="0" max="100" value={d.peso}
                onChange={e => setDim(i, 'peso', e.target.value)} />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>%</span>
              <button onClick={() => removeDim(i)} disabled={form.dimensiones.length <= 2} style={{
                background: 'none', border: 'none', cursor: form.dimensiones.length <= 2 ? 'not-allowed' : 'pointer',
                fontSize: 16, color: 'var(--text-muted)', opacity: form.dimensiones.length <= 2 ? 0.4 : 1,
              }}>×</button>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button variant="ghost" size="sm" onClick={addDim}>+ Agregar dimensión</Button>
          <Badge variant={total === 100 ? 'success' : 'danger'}>
            Total: {total}% {total !== 100 && '(debe sumar 100%)'}
          </Badge>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
          <Button variant="secondary" onClick={onCancel}>Cancelar</Button>
          <Button onClick={guardar} disabled={!valido || guardando}>
            {guardando ? 'Guardando...' : 'Crear plantilla'}
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

export default function Plantillas() {
  const queryClient = useQueryClient()
  const [creando, setCreando] = useState(false)

  const { data } = useQuery({
    queryKey: ['plantillas'],
    queryFn: () => api.get('/entrevista/plantillas').then(r => r.data).catch(() => DEMO),
  })

  const plantillas = data || DEMO

  function agregarPlantilla(nueva) {
    queryClient.setQueryData(['plantillas'], (prev = DEMO) => [...prev, nueva])
    setCreando(false)
  }

  return (
    <div style={{ padding: '20px 24px', maxWidth: 900 }}>
      <PageHeader
        title="Plantillas de evaluación"
        description="Dimensiones y pesos con los que EVA evalúa cada entrevista"
        action={!creando && <Button onClick={() => setCreando(true)}>+ Nueva plantilla</Button>}
      />

      {creando && <Editor onCancel={() => setCreando(false)} onSaved={agregarPlantilla} />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 10 }}>
        {plantillas.map((p, i) => (
          <motion.div key={p.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
            <Card>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                <div>
                  <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{p.nombre}</p>
                  {p.descripcion && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{p.descripcion}</p>}
                </div>
                <Badge variant={p.activa ? 'success' : 'neutral'}>{p.activa ? 'Activa' : 'Inactiva'}</Badge>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {p.dimensiones.map(d => (
                  <div key={d.nombre}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{d.nombre}</span>
                      <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{d.peso}%</span>
                    </div>
                    <div style={{ height: 3, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden' }}>
                      <motion.div
                        initial={{ width: 0 }} animate={{ width: `${d.peso}%` }}
                        transition={{ duration: 0.5, ease: 'easeOut' }}
                        style={{ height: '100%', background: 'var(--text-primary)', borderRadius: 999 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}