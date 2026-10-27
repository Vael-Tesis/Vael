import { useState, type ChangeEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { AreaTexto, Campo, Selector, Volver, estiloControl } from '../../components/ui/Formulario'
import Spinner from '../../components/ui/Spinner'
import {
  CONTRATOS, MODALIDADES, NIVELES, OPCIONES_PRIORIDAD,
  type Contrato, type Modalidad, type Nivel, type Prioridad, type Vacante,
} from './vacantesComun'

/**
 * P-04 Formulario de vacante (HU-08, RF-A-06): crea en borrador con código automático
 * {AREA}-{AÑO}-{NNN}; solo ofrece áreas activas. En edición carga la vacante guardada.
 */

const PASOS = ['Información básica', 'Requisitos', 'Condiciones', 'Configuración de la IA'] as const

interface Formulario {
  titulo: string
  area_id: string
  descripcion: string
  responsabilidades: string
  requisitos: string
  requisitos_deseables: string
  beneficios: string
  habilidades: string
  tecnologias: string
  nivel_experiencia: Nivel
  anios_experiencia: string
  modalidad: Modalidad
  tipo_contrato: Contrato
  ciudad: string
  pais: string
  cantidad_posiciones: string
  salario_minimo: string
  salario_maximo: string
  mostrar_salario: boolean
  confidencial: boolean
  prioridad: Prioridad
  score_cv_minimo: string
  nota_minima_examen: string
  top_candidatos_finalistas: string
  instruccion_ia_extra: string
}

const INICIAL: Formulario = {
  titulo: '', area_id: '', descripcion: '', responsabilidades: '', requisitos: '', requisitos_deseables: '',
  beneficios: '', habilidades: '', tecnologias: '', nivel_experiencia: 'semi_senior', anios_experiencia: '2',
  modalidad: 'presencial', tipo_contrato: 'indefinido', ciudad: '', pais: 'Perú', cantidad_posiciones: '1',
  salario_minimo: '', salario_maximo: '', mostrar_salario: false, confidencial: false, prioridad: 'media',
  score_cv_minimo: '60', nota_minima_examen: '13', top_candidatos_finalistas: '5', instruccion_ia_extra: '',
}

function desdeVacante(v: Vacante): Formulario {
  const texto = (valor: string | null) => valor ?? ''
  const numero = (valor: number | null) => (valor === null ? '' : String(valor))
  return {
    titulo: v.titulo, area_id: v.area_id, descripcion: texto(v.descripcion), responsabilidades: texto(v.responsabilidades),
    requisitos: texto(v.requisitos), requisitos_deseables: texto(v.requisitos_deseables), beneficios: texto(v.beneficios),
    habilidades: v.habilidades.join(', '), tecnologias: v.tecnologias.join(', '),
    nivel_experiencia: v.nivel_experiencia ?? 'semi_senior', anios_experiencia: numero(v.anios_experiencia),
    modalidad: v.modalidad ?? 'presencial', tipo_contrato: v.tipo_contrato ?? 'indefinido',
    ciudad: texto(v.ciudad), pais: texto(v.pais), cantidad_posiciones: String(v.cantidad_posiciones),
    salario_minimo: numero(v.salario_minimo), salario_maximo: numero(v.salario_maximo),
    mostrar_salario: v.mostrar_salario, confidencial: v.confidencial, prioridad: v.prioridad,
    score_cv_minimo: String(v.score_cv_minimo), nota_minima_examen: String(v.nota_minima_examen),
    top_candidatos_finalistas: String(v.top_candidatos_finalistas), instruccion_ia_extra: texto(v.instruccion_ia_extra),
  }
}

function aCuerpo(f: Formulario): Esquemas['VacanteCreateRequest'] {
  const lista = (valor: string) => valor.split(',').map((s) => s.trim()).filter(Boolean)
  const opcional = (valor: string) => valor.trim() || null
  const numeroOpcional = (valor: string) => (valor.trim() === '' ? null : Number(valor))
  return {
    area_id: f.area_id, titulo: f.titulo.trim(), descripcion: opcional(f.descripcion), responsabilidades: opcional(f.responsabilidades),
    requisitos: opcional(f.requisitos), requisitos_deseables: opcional(f.requisitos_deseables), beneficios: opcional(f.beneficios),
    habilidades: lista(f.habilidades), tecnologias: lista(f.tecnologias), nivel_experiencia: f.nivel_experiencia,
    anios_experiencia: numeroOpcional(f.anios_experiencia), modalidad: f.modalidad, tipo_contrato: f.tipo_contrato,
    ciudad: opcional(f.ciudad), pais: opcional(f.pais), salario_minimo: numeroOpcional(f.salario_minimo),
    salario_maximo: numeroOpcional(f.salario_maximo), moneda: 'PEN', mostrar_salario: f.mostrar_salario,
    confidencial: f.confidencial, prioridad: f.prioridad, fecha_limite: null, jefe_directo: null, solicitante: null,
    cantidad_posiciones: Number(f.cantidad_posiciones) || 1, score_cv_minimo: Number(f.score_cv_minimo),
    nota_minima_examen: Number(f.nota_minima_examen), top_candidatos_finalistas: Number(f.top_candidatos_finalistas),
    instruccion_ia_extra: opcional(f.instruccion_ia_extra),
  }
}

function Editor({ vacante }: { vacante?: Vacante }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [paso, setPaso] = useState(0)
  const [form, setForm] = useState<Formulario>(vacante ? desdeVacante(vacante) : INICIAL)

  const areas = useQuery({ queryKey: ['areas'], queryFn: async () => datos(await api.GET('/api/areas')) })
  // Solo áreas activas (V-04); en edición se conserva la actual aunque esté inactiva
  const disponibles = (areas.data ?? []).filter((a) => a.activa || a.id === vacante?.area_id)

  const texto = (clave: keyof Formulario) => ({
    value: String(form[clave]),
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm((f) => ({ ...f, [clave]: e.target.value })),
  })
  const marcar = (clave: 'mostrar_salario' | 'confidencial') => ({
    checked: form[clave],
    onChange: (e: ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [clave]: e.target.checked })),
  })

  const guardar = useMutation({
    mutationFn: async () => {
      const cuerpo = aCuerpo(form)
      return vacante
        ? datos(await api.PUT('/api/vacantes/{vacante_id}', { params: { path: { vacante_id: vacante.id } }, body: cuerpo }))
        : datos(await api.POST('/api/vacantes', { body: cuerpo }))
    },
    onSuccess: (guardada) => {
      toast.success(vacante ? 'Vacante actualizada' : `Vacante creada en borrador: ${guardada.codigo}`)
      queryClient.invalidateQueries({ queryKey: ['vacantes'] })
      queryClient.invalidateQueries({ queryKey: ['vacante', guardada.id] })
      navigate(`/vacantes/${guardada.id}`)
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo guardar la vacante')),
  })

  const pasoValido = paso !== 0 || (form.titulo.trim() !== '' && form.area_id !== '')
  const dosColumnas = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 } as const

  return (
    <>
      <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
        {PASOS.map((p, i) => (
          <div key={p} style={{ flex: 1 }}>
            <div style={{ height: 3, borderRadius: 999, marginBottom: 6, background: i <= paso ? 'var(--brand)' : 'var(--border)', transition: 'background 200ms ease' }} />
            <p style={{ fontSize: 11, color: i === paso ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: i === paso ? 500 : 400 }}>{p}</p>
          </div>
        ))}
      </div>

      <Card>
        <AnimatePresence mode="wait">
          <motion.div key={paso} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.15 }}>
            {paso === 0 && (
              <>
                <Campo etiqueta="Título del puesto" htmlFor="titulo">
                  <input id="titulo" style={estiloControl} placeholder="Desarrollador Backend Python" {...texto('titulo')} />
                </Campo>
                <Campo
                  etiqueta="Área"
                  htmlFor="area"
                  ayuda={areas.data && disponibles.length === 0 && <>No hay áreas activas. <Link to="/areas" style={{ color: 'var(--brand)' }}>Créalas o actívalas en Áreas</Link>.</>}
                >
                  <Selector
                    id="area"
                    valor={form.area_id}
                    deshabilitado={areas.isLoading || disponibles.length === 0}
                    opciones={[{ valor: '', etiqueta: areas.isLoading ? 'Cargando áreas...' : 'Selecciona un área' }, ...disponibles.map((a) => ({ valor: a.id, etiqueta: a.nombre }))]}
                    onCambio={(valor) => setForm((f) => ({ ...f, area_id: valor }))}
                  />
                </Campo>
                <Campo etiqueta="Descripción del puesto" htmlFor="descripcion">
                  <AreaTexto id="descripcion" filas={4} placeholder="Describe el rol y su propósito dentro del equipo" valor={form.descripcion} onChange={texto('descripcion').onChange} />
                </Campo>
                <Campo etiqueta="Responsabilidades" htmlFor="responsabilidades">
                  <AreaTexto id="responsabilidades" placeholder="Principales responsabilidades" valor={form.responsabilidades} onChange={texto('responsabilidades').onChange} />
                </Campo>
              </>
            )}

            {paso === 1 && (
              <>
                <Campo etiqueta="Requisitos obligatorios" htmlFor="requisitos">
                  <AreaTexto id="requisitos" filas={4} placeholder="Requisitos indispensables" valor={form.requisitos} onChange={texto('requisitos').onChange} />
                </Campo>
                <Campo etiqueta="Requisitos deseables" htmlFor="deseables">
                  <AreaTexto id="deseables" placeholder="Suman, pero no son excluyentes" valor={form.requisitos_deseables} onChange={texto('requisitos_deseables').onChange} />
                </Campo>
                <Campo etiqueta="Habilidades (separadas por coma)" htmlFor="habilidades">
                  <input id="habilidades" style={estiloControl} placeholder="Comunicación, trabajo en equipo" {...texto('habilidades')} />
                </Campo>
                <Campo etiqueta="Tecnologías (separadas por coma)" htmlFor="tecnologias">
                  <input id="tecnologias" style={estiloControl} placeholder="Python, FastAPI, PostgreSQL" {...texto('tecnologias')} />
                </Campo>
                <Campo etiqueta="Beneficios" htmlFor="beneficios">
                  <AreaTexto id="beneficios" placeholder="Beneficios que ofrece la empresa" valor={form.beneficios} onChange={texto('beneficios').onChange} />
                </Campo>
              </>
            )}

            {paso === 2 && (
              <>
                <div style={dosColumnas}>
                  <Campo etiqueta="Nivel de experiencia" htmlFor="nivel">
                    <Selector id="nivel" valor={form.nivel_experiencia} opciones={NIVELES} onCambio={(v) => setForm((f) => ({ ...f, nivel_experiencia: v }))} />
                  </Campo>
                  <Campo etiqueta="Años de experiencia" htmlFor="anios">
                    <input id="anios" type="number" min="0" style={estiloControl} {...texto('anios_experiencia')} />
                  </Campo>
                  <Campo etiqueta="Modalidad" htmlFor="modalidad">
                    <Selector id="modalidad" valor={form.modalidad} opciones={MODALIDADES} onCambio={(v) => setForm((f) => ({ ...f, modalidad: v }))} />
                  </Campo>
                  <Campo etiqueta="Tipo de contrato" htmlFor="contrato">
                    <Selector id="contrato" valor={form.tipo_contrato} opciones={CONTRATOS} onCambio={(v) => setForm((f) => ({ ...f, tipo_contrato: v }))} />
                  </Campo>
                  <Campo etiqueta="Ciudad" htmlFor="ciudad">
                    <input id="ciudad" style={estiloControl} placeholder="Lima" {...texto('ciudad')} />
                  </Campo>
                  <Campo etiqueta="Posiciones a cubrir" htmlFor="posiciones">
                    <input id="posiciones" type="number" min="1" style={estiloControl} {...texto('cantidad_posiciones')} />
                  </Campo>
                  <Campo etiqueta="Salario mínimo en soles (opcional)" htmlFor="salario-min">
                    <input id="salario-min" type="number" min="0" style={estiloControl} {...texto('salario_minimo')} />
                  </Campo>
                  <Campo etiqueta="Salario máximo en soles (opcional)" htmlFor="salario-max">
                    <input id="salario-max" type="number" min="0" style={estiloControl} {...texto('salario_maximo')} />
                  </Campo>
                  <Campo etiqueta="Prioridad" htmlFor="prioridad">
                    <Selector id="prioridad" valor={form.prioridad} opciones={OPCIONES_PRIORIDAD} onCambio={(v) => setForm((f) => ({ ...f, prioridad: v }))} />
                  </Campo>
                </div>
                <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginTop: 4 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input type="checkbox" {...marcar('mostrar_salario')} /> Mostrar el salario en la publicación
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    <input type="checkbox" {...marcar('confidencial')} /> Vacante confidencial (no sale en el listado público ni en el feed)
                  </label>
                </div>
              </>
            )}

            {paso === 3 && (
              <>
                <div style={dosColumnas}>
                  <Campo etiqueta="Puntaje mínimo de CV (0-100)" htmlFor="score-cv" ayuda="Criterio de la recomendación de la IA; la decisión es de RRHH">
                    <input id="score-cv" type="number" min="0" max="100" style={estiloControl} {...texto('score_cv_minimo')} />
                  </Campo>
                  <Campo etiqueta="Nota mínima del examen (0-20)" htmlFor="nota-examen">
                    <input id="nota-examen" type="number" min="0" max="20" style={estiloControl} {...texto('nota_minima_examen')} />
                  </Campo>
                </div>
                <Campo etiqueta="Finalistas sugeridos" htmlFor="finalistas">
                  <input id="finalistas" type="number" min="1" style={estiloControl} {...texto('top_candidatos_finalistas')} />
                </Campo>
                <Campo etiqueta="Instrucción adicional para la IA (opcional)" htmlFor="instruccion">
                  <AreaTexto id="instruccion" placeholder="Ej.: valorar experiencia en proyectos de pagos" valor={form.instruccion_ia_extra} onChange={texto('instruccion_ia_extra').onChange} />
                </Campo>
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </Card>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
        <Button variant="secondary" onClick={() => setPaso((p) => Math.max(0, p - 1))} disabled={paso === 0}>Anterior</Button>
        {paso < PASOS.length - 1 ? (
          <Button onClick={() => setPaso((p) => p + 1)} disabled={!pasoValido}>Siguiente</Button>
        ) : (
          <Button onClick={() => guardar.mutate()} disabled={guardar.isPending || form.titulo.trim() === '' || form.area_id === ''}>
            {guardar.isPending ? 'Guardando...' : vacante ? 'Guardar cambios' : 'Crear vacante'}
          </Button>
        )}
      </div>
    </>
  )
}

export default function VacanteForm() {
  const navigate = useNavigate()
  const { id } = useParams()

  const vacante = useQuery({
    queryKey: ['vacante', id],
    enabled: id !== undefined,
    queryFn: async () => datos(await api.GET('/api/vacantes/{vacante_id}', { params: { path: { vacante_id: id ?? '' } } })),
  })

  return (
    <div style={{ padding: '20px 24px', maxWidth: 760 }}>
      <Volver onClick={() => navigate(id ? `/vacantes/${id}` : '/vacantes')}>{id ? 'Volver a la vacante' : 'Volver a vacantes'}</Volver>
      <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 20 }}>
        {id ? `Editar ${vacante.data?.codigo ?? 'vacante'}` : 'Nueva vacante'}
      </h1>
      {id && vacante.isLoading && <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner /></div>}
      {id && vacante.error && <p style={{ color: 'var(--danger-text)', fontSize: 13 }}>{mensajeDe(vacante.error, 'No se pudo cargar la vacante')}</p>}
      {(!id || vacante.data) && <Editor key={vacante.data?.id ?? 'nueva'} vacante={vacante.data} />}
    </div>
  )
}
