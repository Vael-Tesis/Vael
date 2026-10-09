import { useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import Card from '../../components/ui/Card.jsx'
import Button from '../../components/ui/Button.jsx'
import Input from '../../components/ui/Input.jsx'

const PASOS = ['Información básica', 'Requisitos', 'Condiciones', 'Configuración IA']

// Solo se usa como fallback si sinBackend(err) — ver utils/devFallback.js
const AREAS_FALLBACK_DEV = [
  { id: '1', nombre: 'Tecnología', codigo_corto: 'TI' },
  { id: '2', nombre: 'Diseño', codigo_corto: 'DIS' },
  { id: '3', nombre: 'Comercial', codigo_corto: 'COM' },
]

const initialForm = {
  titulo: '', area_id: '', descripcion: '', responsabilidades: '',
  requisitos: '', requisitos_deseables: '', beneficios: '',
  habilidades: '', tecnologias: '',
  nivel_experiencia: 'semi_senior', anios_experiencia: 2,
  modalidad: 'presencial', tipo_contrato: 'indefinido',
  ciudad: '', pais: 'Perú', cantidad_posiciones: 1,
  salario_minimo: '', salario_maximo: '', mostrar_salario: false,
  confidencial: false, prioridad: 'media',
  score_cv_minimo: 60, nota_minima_examen: 13, top_candidatos_finalistas: 5,
  instruccion_ia_extra: '',
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function Select({ value, onChange, options, disabled }) {
  return (
    <select value={value} onChange={onChange} disabled={disabled} style={{
      width: '100%', height: 36, padding: '0 12px',
      border: '1px solid var(--border)', borderRadius: 6,
      background: 'var(--bg-card)', color: 'var(--text-primary)',
      fontSize: 13, outline: 'none',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.6 : 1,
    }}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

function TextArea({ value, onChange, placeholder, rows = 3 }) {
  return (
    <textarea
      value={value} onChange={onChange} placeholder={placeholder} rows={rows}
      style={{
        width: '100%', padding: 10,
        border: '1px solid var(--border)', borderRadius: 6,
        background: 'var(--bg-card)', color: 'var(--text-primary)',
        fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none',
      }}
    />
  )
}

export default function VacanteForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const esEdicion = !!id
  const [paso, setPaso] = useState(0)
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)

  const set = (key) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm(f => ({ ...f, [key]: val }))
  }

  const { data: areas, isLoading: cargandoAreas } = useQuery({
    queryKey: ['areas'],
    queryFn: () => api.get('/areas').then(r => r.data).catch(err => { if (sinBackend(err)) return AREAS_FALLBACK_DEV; throw err }),
  })
  const areasDisponibles = areas || []

  function construirPayload() {
    const dividirLista = (valor) => valor.split(',').map(s => s.trim()).filter(Boolean)
    return {
      ...form,
      habilidades: dividirLista(form.habilidades),
      tecnologias: dividirLista(form.tecnologias),
      salario_minimo: form.salario_minimo === '' ? null : Number(form.salario_minimo),
      salario_maximo: form.salario_maximo === '' ? null : Number(form.salario_maximo),
    }
  }

  async function handleSubmit() {
    setLoading(true)
    try {
      const payload = construirPayload()
      if (esEdicion) {
        await api.put(`/vacantes/${id}`, payload)
        toast.success('Vacante actualizada')
      } else {
        await api.post('/vacantes', payload)
        toast.success('Vacante creada en borrador')
      }
      navigate('/vacantes')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al guardar la vacante')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '20px 24px', maxWidth: 720 }}>
      <button onClick={() => navigate('/vacantes')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', fontSize: 12, marginBottom: 14, padding: 0,
      }}>← Volver a vacantes</button>

      <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 20 }}>
        {esEdicion ? 'Editar vacante' : 'Nueva vacante'}
      </h1>

      {/* Progreso de pasos */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
        {PASOS.map((p, i) => (
          <div key={p} style={{ flex: 1 }}>
            <div style={{
              height: 3, borderRadius: 999, marginBottom: 6,
              background: i <= paso ? 'var(--text-primary)' : 'var(--border)',
              transition: 'background 200ms ease',
            }} />
            <p style={{
              fontSize: 11, color: i === paso ? 'var(--text-primary)' : 'var(--text-muted)',
              fontWeight: i === paso ? 500 : 400,
            }}>{p}</p>
          </div>
        ))}
      </div>

      <Card>
        <AnimatePresence mode="wait">
          <motion.div
            key={paso}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.15 }}
          >
            {/* Paso 0 — Información básica */}
            {paso === 0 && (
              <>
                <Field label="Título del puesto">
                  <Input value={form.titulo} onChange={set('titulo')} placeholder="Full Stack Developer" />
                </Field>
                <Field label="Área">
                  {cargandoAreas ? (
                    <Select value="" onChange={() => {}} disabled options={[{ value: '', label: 'Cargando áreas...' }]} />
                  ) : areasDisponibles.length === 0 ? (
                    <>
                      <Select value="" onChange={() => {}} disabled options={[{ value: '', label: 'No hay áreas disponibles' }]} />
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
                        No hay áreas — <Link to="/areas" style={{ color: 'var(--text-primary)' }}>créalas primero en la sección Áreas</Link>
                      </p>
                    </>
                  ) : (
                    <Select
                      value={form.area_id} onChange={set('area_id')}
                      options={[{ value: '', label: 'Selecciona un área' }, ...areasDisponibles.map(a => ({ value: a.id, label: a.nombre }))]}
                    />
                  )}
                </Field>
                <Field label="Descripción del puesto">
                  <TextArea value={form.descripcion} onChange={set('descripcion')} placeholder="Describe el rol y su propósito dentro del equipo..." rows={4} />
                </Field>
                <Field label="Responsabilidades">
                  <TextArea value={form.responsabilidades} onChange={set('responsabilidades')} placeholder="Principales responsabilidades del puesto..." />
                </Field>
              </>
            )}

            {/* Paso 1 — Requisitos */}
            {paso === 1 && (
              <>
                <Field label="Requisitos obligatorios">
                  <TextArea value={form.requisitos} onChange={set('requisitos')} placeholder="Requisitos indispensables para el puesto..." rows={4} />
                </Field>
                <Field label="Requisitos deseables">
                  <TextArea value={form.requisitos_deseables} onChange={set('requisitos_deseables')} placeholder="Requisitos que suman pero no son excluyentes..." />
                </Field>
                <Field label="Habilidades (separadas por coma)">
                  <Input value={form.habilidades} onChange={set('habilidades')} placeholder="Comunicación, trabajo en equipo, liderazgo" />
                </Field>
                <Field label="Tecnologías (separadas por coma)">
                  <Input value={form.tecnologias} onChange={set('tecnologias')} placeholder="React, Node.js, PostgreSQL, Docker" />
                </Field>
                <Field label="Beneficios">
                  <TextArea value={form.beneficios} onChange={set('beneficios')} placeholder="Beneficios que ofrece la empresa..." />
                </Field>
              </>
            )}

            {/* Paso 2 — Condiciones */}
            {paso === 2 && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="Nivel de experiencia">
                    <Select value={form.nivel_experiencia} onChange={set('nivel_experiencia')} options={[
                      { value: 'practicante', label: 'Practicante' },
                      { value: 'junior', label: 'Junior' },
                      { value: 'semi_senior', label: 'Semi Senior' },
                      { value: 'senior', label: 'Senior' },
                      { value: 'lider', label: 'Líder' },
                    ]} />
                  </Field>
                  <Field label="Años de experiencia">
                    <Input type="number" value={form.anios_experiencia} onChange={set('anios_experiencia')} />
                  </Field>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="Modalidad">
                    <Select value={form.modalidad} onChange={set('modalidad')} options={[
                      { value: 'presencial', label: 'Presencial' },
                      { value: 'remoto', label: 'Remoto' },
                      { value: 'hibrido', label: 'Híbrido' },
                    ]} />
                  </Field>
                  <Field label="Tipo de contrato">
                    <Select value={form.tipo_contrato} onChange={set('tipo_contrato')} options={[
                      { value: 'indefinido', label: 'Indefinido' },
                      { value: 'plazo_fijo', label: 'Plazo fijo' },
                      { value: 'practicas', label: 'Prácticas' },
                      { value: 'freelance', label: 'Freelance' },
                      { value: 'part_time', label: 'Part-time' },
                    ]} />
                  </Field>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="Ciudad">
                    <Input value={form.ciudad} onChange={set('ciudad')} placeholder="Lima" />
                  </Field>
                  <Field label="Posiciones a cubrir">
                    <Input type="number" value={form.cantidad_posiciones} onChange={set('cantidad_posiciones')} />
                  </Field>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="Salario mínimo (opcional)">
                    <Input type="number" value={form.salario_minimo} onChange={set('salario_minimo')} placeholder="3000" />
                  </Field>
                  <Field label="Salario máximo (opcional)">
                    <Input type="number" value={form.salario_maximo} onChange={set('salario_maximo')} placeholder="5000" />
                  </Field>
                </div>
                <div style={{ display: 'flex', gap: 20, marginTop: 4 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input type="checkbox" checked={form.mostrar_salario} onChange={set('mostrar_salario')} />
                    Mostrar salario públicamente
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input type="checkbox" checked={form.confidencial} onChange={set('confidencial')} />
                    Vacante confidencial
                  </label>
                </div>
              </>
            )}

            {/* Paso 3 — Configuración IA */}
            {paso === 3 && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="Score mínimo de CV (0-100)">
                    <Input type="number" value={form.score_cv_minimo} onChange={set('score_cv_minimo')} />
                  </Field>
                  <Field label="Nota mínima de examen (0-20)">
                    <Input type="number" value={form.nota_minima_examen} onChange={set('nota_minima_examen')} />
                  </Field>
                </div>
                <Field label="Candidatos finalistas sugeridos">
                  <Input type="number" value={form.top_candidatos_finalistas} onChange={set('top_candidatos_finalistas')} />
                </Field>
                <Field label="Instrucción adicional para la IA (opcional)">
                  <TextArea
                    value={form.instruccion_ia_extra} onChange={set('instruccion_ia_extra')}
                    placeholder="Ej: Priorizar candidatos con experiencia en startups de rápido crecimiento..."
                  />
                </Field>
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </Card>

      {/* Navegación */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
        <Button variant="secondary" onClick={() => setPaso(p => Math.max(0, p - 1))} disabled={paso === 0}>
          Anterior
        </Button>
        {paso < PASOS.length - 1 ? (
          <Button onClick={() => setPaso(p => p + 1)}>Siguiente</Button>
        ) : (
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Guardando...' : esEdicion ? 'Guardar cambios' : 'Crear vacante'}
          </Button>
        )}
      </div>
    </div>
  )
}