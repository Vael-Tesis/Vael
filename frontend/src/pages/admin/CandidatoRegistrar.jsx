import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
import Card from '../../components/ui/Card.jsx'
import Button from '../../components/ui/Button.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Input from '../../components/ui/Input.jsx'
import FileDrop from '../../components/ui/FileDrop.jsx'

const DEMO_VACANTES = [
  { id: '1', codigo: 'TI-2026-001', titulo: 'Full Stack Developer', estado: 'abierta' },
  { id: '2', codigo: 'TI-2026-002', titulo: 'DevOps Engineer', estado: 'abierta' },
  { id: '3', codigo: 'DIS-2026-001', titulo: 'UX Designer', estado: 'pausada' },
]

const TABS = [
  { key: 'manual', label: 'Registro manual' },
  { key: 'masiva', label: 'Carga masiva' },
]

function SelectVacante({ value, onChange, vacantes }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>
        Vacante
      </label>
      <select value={value} onChange={onChange} style={{
        width: '100%', height: 36, padding: '0 12px',
        border: '1px solid var(--border)', borderRadius: 6,
        background: 'var(--bg-card)', color: 'var(--text-primary)',
        fontSize: 13, outline: 'none',
      }}>
        <option value="">Selecciona una vacante</option>
        {vacantes.map(v => (
          <option key={v.id} value={v.id}>{v.codigo} · {v.titulo}</option>
        ))}
      </select>
    </div>
  )
}

const MULTIPART = { headers: { 'Content-Type': 'multipart/form-data' } }

export default function CandidatoRegistrar() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('manual')
  const [enviando, setEnviando] = useState(false)

  // Manual
  const [form, setForm] = useState({ nombre: '', apellidos: '', email: '', telefono: '', vacante_id: '' })
  const [cv, setCv] = useState(null)

  // Masiva
  const [vacanteMasiva, setVacanteMasiva] = useState('')
  const [archivos, setArchivos] = useState([])
  const [resultado, setResultado] = useState(null)

  const { data } = useQuery({
    queryKey: ['vacantes-select'],
    queryFn: () => api.get('/vacantes').then(r => r.data).catch(() => DEMO_VACANTES),
  })
  const vacantes = (data || DEMO_VACANTES).filter(v => v.estado !== 'cerrada')

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  async function guardarManual(e) {
    e.preventDefault()
    if (!form.vacante_id) return toast.error('Selecciona una vacante')
    if (!cv) return toast.error('Adjunta el CV en PDF')

    setEnviando(true)
    const fd = new FormData()
    Object.entries(form).forEach(([k, v]) => fd.append(k, v))
    fd.append('cv', cv)

    try {
      await api.post('/candidatos', fd, MULTIPART)
      toast.success('Candidato registrado')
      navigate('/candidatos')
    } catch (err) {
      if (sinBackend(err)) {
        toast.success('Candidato registrado (modo desarrollo)')
        navigate('/candidatos')
      } else {
        toast.error(err.response?.data?.detail || 'No se pudo registrar el candidato')
      }
    } finally {
      setEnviando(false)
    }
  }

  function agregarArchivos(nuevos) {
    setArchivos(prev => {
      const claves = new Set(prev.map(f => `${f.name}-${f.size}`))
      return [...prev, ...nuevos.filter(f => !claves.has(`${f.name}-${f.size}`))]
    })
  }

  async function procesarMasiva() {
    if (!vacanteMasiva) return toast.error('Selecciona una vacante')
    setEnviando(true)
    const fd = new FormData()
    fd.append('vacante_id', vacanteMasiva)
    archivos.forEach(f => fd.append('archivos', f))

    try {
      const { data } = await api.post('/candidatos/carga-masiva', fd, MULTIPART)
      setResultado(data)
    } catch (err) {
      if (sinBackend(err)) {
        setResultado({
          total: archivos.length, exitosos: archivos.length, fallidos: 0,
          detalle: archivos.map((f, i) => ({ archivo: f.name, estado: 'ok', candidato_id: i + 1 })),
        })
      } else {
        toast.error(err.response?.data?.detail || 'No se pudo procesar la carga')
      }
    } finally {
      setEnviando(false)
    }
  }

  function reiniciarMasiva() {
    setArchivos([])
    setResultado(null)
  }

  return (
    <div style={{ padding: '20px 24px', maxWidth: 720 }}>
      <button onClick={() => navigate('/candidatos')} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', fontSize: 12, marginBottom: 14, padding: 0,
      }}>← Volver a candidatos</button>

      <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>Registrar candidatos</h1>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
        Agrega candidatos de forma individual o sube varios CVs a la vez
      </p>

      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 16 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            padding: '8px 14px', fontSize: 13, fontWeight: 500,
            color: tab === t.key ? 'var(--text-primary)' : 'var(--text-muted)',
            borderBottom: tab === t.key ? '2px solid var(--text-primary)' : '2px solid transparent',
            marginBottom: -1,
          }}>{t.label}</button>
        ))}
      </div>

      <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>

        {/* ── Manual ── */}
        {tab === 'manual' && (
          <Card>
            <form onSubmit={guardarManual} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <SelectVacante value={form.vacante_id} onChange={set('vacante_id')} vacantes={vacantes} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Input label="Nombres" value={form.nombre} onChange={set('nombre')} required />
                <Input label="Apellidos" value={form.apellidos} onChange={set('apellidos')} required />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Input label="Correo electrónico" type="email" value={form.email} onChange={set('email')} required />
                <Input label="Teléfono" value={form.telefono} onChange={set('telefono')} />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>CV</label>
                {cv ? (
                  <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 12px', background: 'var(--bg-page)',
                    border: '1px solid var(--border)', borderRadius: 8, fontSize: 13,
                  }}>
                    <span style={{ color: 'var(--text-primary)' }}>{cv.name}</span>
                    <button type="button" onClick={() => setCv(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--text-muted)' }}>Quitar</button>
                  </div>
                ) : (
                  <FileDrop onFiles={files => setCv(files[0])} />
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 }}>
                <Button variant="secondary" onClick={() => navigate('/candidatos')}>Cancelar</Button>
                <Button type="submit" disabled={enviando}>{enviando ? 'Guardando...' : 'Registrar candidato'}</Button>
              </div>
            </form>
          </Card>
        )}

        {/* ── Masiva ── */}
        {tab === 'masiva' && !resultado && (
          <Card>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <SelectVacante value={vacanteMasiva} onChange={e => setVacanteMasiva(e.target.value)} vacantes={vacantes} />
              <FileDrop multiple onFiles={agregarArchivos} hint="Arrastra varios CVs aquí o haz clic para seleccionar" />

              {archivos.length > 0 && (
                <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
                  {archivos.map((f, i) => (
                    <div key={`${f.name}-${f.size}`} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '8px 12px', fontSize: 13,
                      borderBottom: i < archivos.length - 1 ? '1px solid var(--border)' : 'none',
                    }}>
                      <span style={{ color: 'var(--text-primary)' }}>{f.name}</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(f.size / 1024).toFixed(0)} KB</span>
                        <button onClick={() => setArchivos(a => a.filter(x => x !== f))} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--text-muted)' }}>Quitar</button>
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                <Button onClick={procesarMasiva} disabled={enviando || archivos.length === 0}>
                  {enviando ? 'Procesando...' : `Procesar ${archivos.length || ''} CV${archivos.length === 1 ? '' : 's'}`}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {tab === 'masiva' && resultado && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 12 }}>
              {[
                { label: 'Total', valor: resultado.total, color: 'var(--text-primary)' },
                { label: 'Exitosos', valor: resultado.exitosos, color: 'var(--success-text)' },
                { label: 'Fallidos', valor: resultado.fallidos, color: resultado.fallidos ? 'var(--danger-text)' : 'var(--text-muted)' },
              ].map(s => (
                <Card key={s.label}>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{s.label}</p>
                  <p style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.5px', color: s.color }}>{s.valor}</p>
                </Card>
              ))}
            </div>

            <Card padding="0">
              {resultado.detalle.map((d, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '9px 16px', fontSize: 13,
                  borderBottom: i < resultado.detalle.length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  <span style={{ color: 'var(--text-primary)' }}>{d.archivo}</span>
                  {d.estado === 'ok'
                    ? <Badge variant="success">Cargado</Badge>
                    : <Badge variant="danger">{d.motivo || 'Error'}</Badge>}
                </div>
              ))}
            </Card>

            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '12px 0' }}>
              Los CVs se analizan en segundo plano. Los scores aparecerán en la lista de candidatos en unos minutos.
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button variant="secondary" onClick={reiniciarMasiva}>Cargar más</Button>
              <Button onClick={() => navigate('/candidatos')}>Ver candidatos</Button>
            </div>
          </>
        )}
      </motion.div>
    </div>
  )
}