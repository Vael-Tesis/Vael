import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../services/api.js'
import { sinBackend } from '../utils/devFallback.js'
import Badge from '../components/ui/Badge.jsx'
import Button from '../components/ui/Button.jsx'
import Input from '../components/ui/Input.jsx'
import FileDrop from '../components/ui/FileDrop.jsx'
import Spinner from '../components/ui/Spinner.jsx'

const DEMO = {
  codigo: 'TI-2026-001', titulo: 'Full Stack Developer',
  area: { nombre: 'Tecnología' }, ciudad: 'Lima',
  modalidad: 'hibrido', tipo_contrato: 'indefinido',
  mostrar_salario: true, salario_minimo: 4000, salario_maximo: 6000, moneda: 'PEN',
  descripcion: 'Buscamos un desarrollador Full Stack para unirse a nuestro equipo de producto y construir funcionalidades de punta a punta.',
  requisitos: '• 3+ años de experiencia con React y Node.js\n• Conocimiento de bases de datos relacionales\n• Experiencia con Git y trabajo en equipo',
  tecnologias: 'React, Node.js, PostgreSQL, Docker, AWS',
  beneficios: '• Trabajo híbrido\n• Seguro de salud\n• Capacitaciones y certificaciones',
}

const MODALIDAD = { presencial: 'Presencial', remoto: 'Remoto', hibrido: 'Híbrido' }
const CONTRATO = { indefinido: 'Indefinido', plazo_fijo: 'Plazo fijo', practicas: 'Prácticas', freelance: 'Freelance', part_time: 'Part-time' }

const initialForm = { nombre: '', apellidos: '', email: '', telefono: '', linkedin: '', pretension_salarial: '' }

function Bloque({ titulo, children }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <p style={{
        fontSize: 11, fontWeight: 500, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6,
      }}>{titulo}</p>
      {children}
    </div>
  )
}

export default function Postular() {
  const { codigo } = useParams()
  const [form, setForm] = useState(initialForm)
  const [cv, setCv] = useState(null)
  const [acepta, setAcepta] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(null)

  const { data: v, isLoading, isError } = useQuery({
    queryKey: ['postular', codigo],
    retry: false,
    queryFn: () => api.get(`/publico/postular/${codigo}`).then(r => r.data)
      .catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    if (!cv) return toast.error('Adjunta tu CV en formato PDF')
    if (!acepta) return toast.error('Debes aceptar el tratamiento de datos para continuar')

    setEnviando(true)
    const fd = new FormData()
    Object.entries(form).forEach(([k, val]) => { if (val !== '') fd.append(k, val) })
    fd.append('acepta_terminos', 'true')
    fd.append('cv', cv)

    try {
      const { data } = await api.post(`/publico/postular/${codigo}/enviar`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setEnviado(data.mensaje || 'OK')
    } catch (err) {
      if (sinBackend(err)) {
        setEnviado('Postulación recibida correctamente (simulado)')
        toast.message('Modo desarrollo: envío simulado')
      } else {
        toast.error(err.response?.data?.detail || 'No se pudo enviar tu postulación')
      }
    } finally {
      setEnviando(false)
    }
  }

  if (isLoading) {
    return <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}><Spinner /></div>
  }

  if (isError) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 20px' }}>
        <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
          Esta vacante no está disponible
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Puede que ya haya cerrado o que el enlace sea incorrecto.
        </p>
      </div>
    )
  }

  if (enviado) {
    return (
      <div style={{ minHeight: 'calc(100vh - 52px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          style={{
            width: '100%', maxWidth: 420, textAlign: 'center',
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 10, padding: 36,
          }}
        >
          <div style={{
            width: 48, height: 48, borderRadius: '50%',
            background: 'var(--success-bg)', color: 'var(--success-text)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, margin: '0 auto 16px',
          }}>✓</div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
            Postulación recibida
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: 16 }}>
            Analizaremos tu perfil para <strong>{v.titulo}</strong>. Si avanzas en el proceso, recibirás un correo con los siguientes pasos.
          </p>
          {enviado !== 'OK' && (
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {enviado}
            </p>
          )}
        </motion.div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '32px 20px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 24, alignItems: 'start' }}>

        {/* Info de la vacante */}
        <div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
            <Badge variant="info">{v.area?.nombre}</Badge>
            <Badge>{MODALIDAD[v.modalidad] || v.modalidad}</Badge>
            <Badge>{v.ciudad}</Badge>
            <Badge>{CONTRATO[v.tipo_contrato] || v.tipo_contrato}</Badge>
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.5px', color: 'var(--text-primary)', marginBottom: 6 }}>
            {v.titulo}
          </h1>
          {v.mostrar_salario && v.salario_minimo && (
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 20 }}>
              {v.moneda} {Number(v.salario_minimo).toLocaleString()} – {Number(v.salario_maximo).toLocaleString()} mensual
            </p>
          )}

          <Bloque titulo="Sobre el puesto">
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{v.descripcion}</p>
          </Bloque>
          <Bloque titulo="Requisitos">
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{v.requisitos}</p>
          </Bloque>
          {v.tecnologias && (
            <Bloque titulo="Tecnologías">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {v.tecnologias.split(',').map(t => t.trim()).filter(Boolean).map(t => (
                  <Badge key={t} variant="info">{t}</Badge>
                ))}
              </div>
            </Bloque>
          )}
          {v.beneficios && (
            <Bloque titulo="Beneficios">
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{v.beneficios}</p>
            </Bloque>
          )}
        </div>

        {/* Formulario */}
        <form
          onSubmit={handleSubmit}
          style={{
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 10, padding: 24,
            position: 'sticky', top: 20,
          }}
        >
          <h2 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>
            Postula a esta vacante
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Input label="Nombres" value={form.nombre} onChange={set('nombre')} required />
              <Input label="Apellidos" value={form.apellidos} onChange={set('apellidos')} required />
            </div>
            <Input label="Correo electrónico" type="email" value={form.email} onChange={set('email')} placeholder="tu@correo.com" required />
            <Input label="Teléfono" value={form.telefono} onChange={set('telefono')} placeholder="987 654 321" required />
            <Input label="LinkedIn (opcional)" value={form.linkedin} onChange={set('linkedin')} placeholder="linkedin.com/in/tu-perfil" />
            <Input label="Pretensión salarial (opcional)" type="number" value={form.pretension_salarial} onChange={set('pretension_salarial')} />

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>
                Tu CV
              </label>
              {cv ? (
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 12px', background: 'var(--bg-page)',
                  border: '1px solid var(--border)', borderRadius: 8, fontSize: 13,
                }}>
                  <span style={{ color: 'var(--text-primary)' }}>{cv.name}</span>
                  <button type="button" onClick={() => setCv(null)} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    fontSize: 12, color: 'var(--text-muted)',
                  }}>Quitar</button>
                </div>
              ) : (
                <FileDrop onFiles={files => setCv(files[0])} />
              )}
            </div>

            <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer', lineHeight: 1.5 }}>
              <input type="checkbox" checked={acepta} onChange={e => setAcepta(e.target.checked)} style={{ marginTop: 2 }} />
              Acepto el tratamiento de mis datos personales mediante inteligencia artificial para evaluar mi postulación.
            </label>

            <Button type="submit" disabled={enviando} style={{ width: '100%', justifyContent: 'center' }}>
              {enviando ? 'Enviando...' : 'Enviar postulación'}
            </Button>
          </div>

          <p style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center', marginTop: 14 }}>
            Powered by VAEL
          </p>
        </form>
      </div>
    </div>
  )
}