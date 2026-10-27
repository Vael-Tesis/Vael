import { useState, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import FileDrop from '../../components/ui/FileDrop'
import { Campo, Pestanas, Selector, Volver, estiloControl, type Opcion } from '../../components/ui/Formulario'

/**
 * P-07 Registrar candidatos (HU-11, RF-A-09): registro manual y carga masiva (pestaña) de CV
 * en PDF. La carga masiva solo ofrece vacantes abiertas e informa qué archivos fallaron y
 * por qué. Cada candidato creado dispara el análisis del CV.
 */

type Pestana = 'manual' | 'masiva'
type ResultadoCarga = Esquemas['CargaMasivaResponse']

const PESTANAS: readonly Opcion<Pestana>[] = [
  { valor: 'manual', etiqueta: 'Registro manual' },
  { valor: 'masiva', etiqueta: 'Carga masiva' },
]

interface DatosManual {
  vacante_id: string
  nombre: string
  apellidos: string
  email: string
  telefono: string
  linkedin: string
  github: string
  portfolio: string
}

const VACIO: DatosManual = { vacante_id: '', nombre: '', apellidos: '', email: '', telefono: '', linkedin: '', github: '', portfolio: '' }

function formData(campos: Record<string, string>, archivos: Record<string, File | File[]>): FormData {
  const fd = new FormData()
  for (const [clave, valor] of Object.entries(campos)) if (valor.trim()) fd.append(clave, valor.trim())
  for (const [clave, valor] of Object.entries(archivos)) for (const archivo of [valor].flat()) fd.append(clave, archivo)
  return fd
}

function Manual({ vacantes }: { vacantes: Opcion<string>[] }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form, setForm] = useState<DatosManual>(VACIO)
  const [cv, setCv] = useState<File | null>(null)
  const valido = form.vacante_id !== '' && form.nombre.trim() !== '' && form.apellidos.trim() !== '' && form.email.trim() !== '' && cv !== null

  const campo = (clave: keyof DatosManual) => ({
    value: form[clave],
    onChange: (e: ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [clave]: e.target.value })),
  })

  const registrar = useMutation({
    mutationFn: async () => {
      if (!cv) throw new Error('Falta el CV')
      const { vacante_id, nombre, apellidos, email } = form
      return datos(
        await api.POST('/api/candidatos', {
          // El cuerpo tipado verifica los campos; el archivo real viaja en el FormData
          body: { vacante_id, nombre, apellidos, email, cv: cv.name },
          bodySerializer: () => formData({ ...form }, { cv }),
        }),
        'No se pudo registrar al candidato',
      )
    },
    onSuccess: (candidato) => {
      toast.success('Candidato registrado; su CV se está analizando')
      queryClient.invalidateQueries({ queryKey: ['candidatos'] })
      navigate(`/candidatos/${candidato.id}`)
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo registrar al candidato')),
  })

  return (
    <Card>
      <Campo etiqueta="Vacante" htmlFor="vacante">
        <Selector id="vacante" valor={form.vacante_id} onCambio={(v) => setForm((f) => ({ ...f, vacante_id: v }))}
          opciones={[{ valor: '', etiqueta: 'Selecciona una vacante' }, ...vacantes]} />
      </Campo>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
        <Campo etiqueta="Nombres" htmlFor="nombre"><input id="nombre" style={estiloControl} {...campo('nombre')} /></Campo>
        <Campo etiqueta="Apellidos" htmlFor="apellidos"><input id="apellidos" style={estiloControl} {...campo('apellidos')} /></Campo>
        <Campo etiqueta="Correo" htmlFor="email"><input id="email" type="email" style={estiloControl} {...campo('email')} /></Campo>
        <Campo etiqueta="Teléfono (opcional)" htmlFor="telefono"><input id="telefono" style={estiloControl} {...campo('telefono')} /></Campo>
        <Campo etiqueta="LinkedIn (opcional)" htmlFor="linkedin"><input id="linkedin" style={estiloControl} {...campo('linkedin')} /></Campo>
        <Campo etiqueta="GitHub (opcional)" htmlFor="github"><input id="github" style={estiloControl} {...campo('github')} /></Campo>
      </div>
      <Campo etiqueta="CV en PDF">
        <FileDrop onFiles={(archivos) => setCv(archivos[0] ?? null)} />
        {cv && <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6 }}>Seleccionado: {cv.name}</p>}
      </Campo>
      <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 14, borderTop: '1px solid var(--border)' }}>
        <Button onClick={() => registrar.mutate()} disabled={!valido || registrar.isPending}>
          {registrar.isPending ? 'Registrando...' : 'Registrar candidato'}
        </Button>
      </div>
    </Card>
  )
}

function Masiva({ vacantes }: { vacantes: Opcion<string>[] }) {
  const queryClient = useQueryClient()
  const [vacanteId, setVacanteId] = useState('')
  const [archivos, setArchivos] = useState<File[]>([])
  const [resultado, setResultado] = useState<ResultadoCarga | null>(null)

  const cargar = useMutation({
    mutationFn: async () =>
      datos(
        await api.POST('/api/candidatos/carga-masiva', {
          body: { vacante_id: vacanteId, archivos: archivos.map((a) => a.name) },
          bodySerializer: () => formData({ vacante_id: vacanteId }, { archivos }),
        }),
        'No se pudo procesar la carga',
      ),
    onSuccess: (r) => {
      setResultado(r)
      setArchivos([])
      queryClient.invalidateQueries({ queryKey: ['candidatos'] })
      if (r.fallidos.length === 0) toast.success(`${r.creados} candidatos creados`)
      else toast.warning(`${r.creados} creados, ${r.fallidos.length} con problemas`)
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo procesar la carga')),
  })

  if (resultado) {
    return (
      <Card>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
          {resultado.creados} {resultado.creados === 1 ? 'candidato creado' : 'candidatos creados'}
        </p>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Sus CV se están analizando; aparecerán en la bandeja cuando la IA termine.
        </p>
        {resultado.fallidos.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--danger-text)', marginBottom: 6 }}>Archivos que no se cargaron</p>
            <ul style={{ fontSize: 13, color: 'var(--text-secondary)', paddingLeft: 18 }}>
              {resultado.fallidos.map((f) => <li key={f.nombre}><strong>{f.nombre}</strong>: {f.motivo}</li>)}
            </ul>
          </div>
        )}
        <Button variant="secondary" onClick={() => setResultado(null)}>Cargar más CV</Button>
      </Card>
    )
  }

  return (
    <Card>
      <Campo etiqueta="Vacante (solo abiertas)" htmlFor="vacante-masiva">
        <Selector id="vacante-masiva" valor={vacanteId} onCambio={setVacanteId}
          opciones={[{ valor: '', etiqueta: vacantes.length ? 'Selecciona una vacante' : 'No hay vacantes abiertas' }, ...vacantes]} />
      </Campo>
      <FileDrop multiple onFiles={(nuevos) => setArchivos((a) => [...a, ...nuevos])} hint="Arrastra varios CV en PDF o haz clic para seleccionarlos" />
      {archivos.length > 0 && (
        <ul style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '10px 0 0', paddingLeft: 18 }}>
          {archivos.map((a, i) => (
            <li key={`${a.name}-${i}`}>
              {a.name}{' '}
              <button type="button" onClick={() => setArchivos((lista) => lista.filter((_, j) => j !== i))}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }} aria-label={`Quitar ${a.name}`}>×</button>
            </li>
          ))}
        </ul>
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
        <Button onClick={() => cargar.mutate()} disabled={vacanteId === '' || archivos.length === 0 || cargar.isPending}>
          {cargar.isPending ? 'Cargando...' : `Cargar ${archivos.length || ''} CV`}
        </Button>
      </div>
    </Card>
  )
}

export default function CandidatoRegistrar() {
  const navigate = useNavigate()
  const [pestana, setPestana] = useState<Pestana>('manual')
  const vacantes = useQuery({ queryKey: ['vacantes', 'todas'], queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })) })

  const todas = (vacantes.data ?? []).filter((v) => v.estado !== 'cerrada').map((v) => ({ valor: v.id, etiqueta: `${v.titulo} (${v.codigo})` }))
  const abiertas = (vacantes.data ?? []).filter((v) => v.estado === 'abierta').map((v) => ({ valor: v.id, etiqueta: `${v.titulo} (${v.codigo})` }))

  return (
    <div style={{ padding: '20px 24px', maxWidth: 760 }}>
      <Volver onClick={() => navigate('/candidatos')}>Volver a candidatos</Volver>
      <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 16 }}>Agregar candidatos</h1>
      <Pestanas actual={pestana} opciones={PESTANAS} onCambio={setPestana} />
      <motion.div key={pestana} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>
        {pestana === 'manual' ? <Manual vacantes={todas} /> : <Masiva vacantes={abiertas} />}
      </motion.div>
    </div>
  )
}
