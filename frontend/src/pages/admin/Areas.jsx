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
  { id: '1', nombre: 'Tecnología', codigo_corto: 'TI', activa: true, _count: { vacantes: 3 } },
  { id: '2', nombre: 'Diseño', codigo_corto: 'DIS', activa: true, _count: { vacantes: 1 } },
  { id: '3', nombre: 'Comercial', codigo_corto: 'COM', activa: true, _count: { vacantes: 1 } },
  { id: '4', nombre: 'Recursos Humanos', codigo_corto: 'RRHH', activa: true, _count: { vacantes: 0 } },
  { id: '5', nombre: 'Finanzas', codigo_corto: 'FIN', activa: false, _count: { vacantes: 0 } },
]

const inputStyle = {
  height: 34, padding: '0 10px', border: '1px solid var(--border)',
  borderRadius: 6, background: 'var(--bg-card)', color: 'var(--text-primary)',
  fontSize: 13, outline: 'none',
}

function Editor({ onCancel, onCreada }) {
  const [form, setForm] = useState({ nombre: '', codigo_corto: '', descripcion: '', instruccion_ia: '' })
  const [guardando, setGuardando] = useState(false)

  const valido = form.nombre.trim() && form.codigo_corto.trim()

  async function guardar() {
    setGuardando(true)
    try {
      await api.post('/areas', form)
      toast.success('Área creada')
      onCreada()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se pudo crear el área')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 16 }}>
      <Card>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 14 }}>Nueva área</p>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10, marginBottom: 10 }}>
          <input style={inputStyle} placeholder="Nombre del área" value={form.nombre}
            onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} />
          <input style={inputStyle} placeholder="Código corto (ej: TI)" maxLength={10} value={form.codigo_corto}
            onChange={e => setForm(f => ({ ...f, codigo_corto: e.target.value }))} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
          <input style={inputStyle} placeholder="Descripción (opcional)" value={form.descripcion}
            onChange={e => setForm(f => ({ ...f, descripcion: e.target.value }))} />
          <input style={inputStyle} placeholder="Instrucción para la IA al evaluar CVs (opcional)" value={form.instruccion_ia}
            onChange={e => setForm(f => ({ ...f, instruccion_ia: e.target.value }))} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
          <Button variant="secondary" onClick={onCancel}>Cancelar</Button>
          <Button onClick={guardar} disabled={!valido || guardando}>
            {guardando ? 'Guardando...' : 'Crear área'}
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

export default function Areas() {
  const queryClient = useQueryClient()
  const [creando, setCreando] = useState(false)

  const { data } = useQuery({
    queryKey: ['areas'],
    queryFn: () => api.get('/areas').then(r => r.data).catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const areas = data || DEMO

  function onAreaCreada() {
    queryClient.invalidateQueries({ queryKey: ['areas'] })
    setCreando(false)
  }

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Áreas"
        description="Áreas organizacionales de la empresa"
        action={!creando && <Button onClick={() => setCreando(true)}>+ Nueva área</Button>}
      />

      {creando && <Editor onCancel={() => setCreando(false)} onCreada={onAreaCreada} />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        {areas.map((a, i) => (
          <motion.div key={a.id}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <Card>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 8,
                  background: 'var(--bg-page)',
                  border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)',
                }}>
                  {a.codigo_corto}
                </div>
                <Badge variant={a.activa ? 'success' : 'neutral'}>
                  {a.activa ? 'Activa' : 'Inactiva'}
                </Badge>
              </div>
              <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>
                {a.nombre}
              </p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {a._count?.vacantes || 0} vacante{a._count?.vacantes !== 1 ? 's' : ''} activa{a._count?.vacantes !== 1 ? 's' : ''}
              </p>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}