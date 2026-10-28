import { useState, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import { AreaTexto, Pestanas, Volver, type Opcion } from '../../components/ui/Formulario'
import Spinner from '../../components/ui/Spinner'
import { ESTADOS_CANDIDATO } from './candidatosComun'
import { CONTRATOS, ESTADOS, MODALIDADES, NIVELES, etiquetaDe, type Vacante } from './vacantesComun'

/**
 * P-05 Detalle de vacante (HU-09, HU-10): publicar, pausar ("despublicar"), reactivar,
 * cerrar y duplicar; textos de difusión generados por la IA, editables y guardados.
 */

type Pestana = 'info' | 'candidatos' | 'publicacion'
type Accion = 'publicar' | 'pausar' | 'cerrar'

const PESTANAS: readonly Opcion<Pestana>[] = [
  { valor: 'info', etiqueta: 'Información' },
  { valor: 'candidatos', etiqueta: 'Candidatos' },
  { valor: 'publicacion', etiqueta: 'Publicación' },
]

const CANALES: Record<string, string> = { linkedin: 'LinkedIn', whatsapp: 'WhatsApp', indeed: 'Indeed' }

const MENSAJE_ACCION: Record<Accion, string> = { publicar: 'Vacante publicada', pausar: 'Vacante pausada', cerrar: 'Vacante cerrada' }

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{titulo}</p>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{children}</div>
    </div>
  )
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: ReactNode }) {
  return (
    <div>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>{etiqueta}</p>
      <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{valor}</p>
    </div>
  )
}

function Informacion({ vacante }: { vacante: Vacante }) {
  return (
    <Card>
      {vacante.descripcion && <Seccion titulo="Descripción">{vacante.descripcion}</Seccion>}
      {vacante.responsabilidades && <Seccion titulo="Responsabilidades">{vacante.responsabilidades}</Seccion>}
      {vacante.requisitos && <Seccion titulo="Requisitos">{vacante.requisitos}</Seccion>}
      {vacante.requisitos_deseables && <Seccion titulo="Deseables">{vacante.requisitos_deseables}</Seccion>}
      {(vacante.habilidades.length > 0 || vacante.tecnologias.length > 0) && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
          {[...vacante.habilidades, ...vacante.tecnologias].map((t) => <Badge key={t} variant="info">{t}</Badge>)}
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
        <Dato etiqueta="Posiciones" valor={vacante.cantidad_posiciones} />
        <Dato etiqueta="Nivel" valor={etiquetaDe(NIVELES, vacante.nivel_experiencia) || '—'} />
        <Dato etiqueta="Contrato" valor={etiquetaDe(CONTRATOS, vacante.tipo_contrato) || '—'} />
        <Dato etiqueta="Puntaje mínimo de CV" valor={`${vacante.score_cv_minimo}/100`} />
        <Dato etiqueta="Nota mínima del examen" valor={`${vacante.nota_minima_examen}/20`} />
        <Dato etiqueta="Finalistas sugeridos" valor={vacante.top_candidatos_finalistas} />
      </div>
    </Card>
  )
}

function Candidatos({ vacante }: { vacante: Vacante }) {
  const navigate = useNavigate()
  const candidatos = useQuery({
    queryKey: ['candidatos', { vacante_id: vacante.id }],
    queryFn: async () => datos(await api.GET('/api/candidatos', { params: { query: { vacante_id: vacante.id } } })),
  })
  if (candidatos.isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}><Spinner /></div>
  if (!candidatos.data?.length) return <Card><EmptyState title="Aún no hay candidatos para esta vacante" /></Card>
  return (
    <Card padding="0">
      {candidatos.data.map((c, i) => (
        <div key={c.id} style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', flexWrap: 'wrap',
          borderBottom: i < candidatos.data.length - 1 ? '1px solid var(--border)' : 'none',
        }}>
          <span style={{ flex: '1 1 180px', fontSize: 13, color: 'var(--text-primary)' }}>{c.nombre} {c.apellidos}</span>
          <Badge variant={ESTADOS_CANDIDATO[c.estado].variante}>{ESTADOS_CANDIDATO[c.estado].etiqueta}</Badge>
          {c.score_cv !== null && <Badge variant="info">CV {c.score_cv}</Badge>}
          <Button variant="secondary" size="sm" onClick={() => navigate(`/candidatos/${c.id}`)}>Ver</Button>
        </div>
      ))}
    </Card>
  )
}

function IconoCopiar({ copiado }: { copiado: boolean }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {copiado
        ? <polyline points="20 6 9 17 4 12" />
        : <><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></>}
    </svg>
  )
}

/** Enlace público de postulación: lo sirve `GET /api/publico/postular/{codigo}`, que solo responde con la
 *  vacante abierta (también si es confidencial: el código hace de enlace privado). Un clic lo copia. */
function EnlacePostulacion({ vacante }: { vacante: Vacante }) {
  const [copiado, setCopiado] = useState(false)
  const enlace = `${window.location.origin}/postular/${vacante.codigo}`
  const disponible = vacante.estado === 'abierta'

  async function copiar() {
    try {
      await navigator.clipboard.writeText(enlace)
      setCopiado(true)
      toast.success('Enlace copiado')
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      toast.error('No se pudo copiar; selecciona el enlace y cópialo a mano')
    }
  }

  return (
    <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Enlace de postulación</p>
      {disponible ? (
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 6 }}>
          <button type="button" onClick={copiar} title="Clic para copiar"
            style={{ flex: 1, minWidth: 0, textAlign: 'left', padding: 10, background: 'var(--bg-page)', border: '1px solid var(--border)', borderRadius: 6, fontFamily: 'monospace', fontSize: 12, color: 'var(--brand)', wordBreak: 'break-all', cursor: 'pointer' }}>
            {enlace}
          </button>
          <button type="button" onClick={copiar} aria-label="Copiar enlace de postulación" title="Copiar"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 12px', background: copiado ? 'var(--success-bg)' : 'var(--bg-page)', border: '1px solid var(--border)', borderRadius: 6, color: copiado ? 'var(--success-text)' : 'var(--text-secondary)', cursor: 'pointer' }}>
            <IconoCopiar copiado={copiado} />
          </button>
        </div>
      ) : (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Disponible cuando la vacante está abierta. Publícala para recibir postulaciones.</p>
      )}
      {disponible && vacante.confidencial && (
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
          Vacante confidencial: no aparece en el listado público ni en el feed; solo quien tenga este enlace puede postular.
        </p>
      )}
    </div>
  )
}

function Publicacion({ vacante }: { vacante: Vacante }) {
  const queryClient = useQueryClient()
  const [borrador, setBorrador] = useState<Record<string, string> | null>(null)

  const guardados = useQuery({
    queryKey: ['vacante', vacante.id, 'textos'],
    queryFn: async () => datos(await api.GET('/api/vacantes/{vacante_id}/textos', { params: { path: { vacante_id: vacante.id } } })),
  })
  const textos = borrador ?? guardados.data?.textos ?? {}

  const generar = useMutation({
    mutationFn: async () =>
      datos(await api.POST('/api/vacantes/{vacante_id}/generar-textos', { params: { path: { vacante_id: vacante.id } } })),
    onSuccess: (r) => {
      setBorrador(r.textos)
      toast.success('Textos generados: revísalos y guárdalos')
    },
    // CA-10: si la IA falla, se informa y la vacante sigue igual
    onError: (e) => toast.error(mensajeDe(e, 'La IA no pudo generar los textos; intenta de nuevo')),
  })

  const guardar = useMutation({
    mutationFn: async () =>
      datos(await api.PUT('/api/vacantes/{vacante_id}/textos', { params: { path: { vacante_id: vacante.id } }, body: { textos } })),
    onSuccess: () => {
      toast.success('Textos guardados')
      setBorrador(null)
      queryClient.invalidateQueries({ queryKey: ['vacante', vacante.id, 'textos'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudieron guardar los textos')),
  })

  const feedDisponible = vacante.estado === 'abierta' && !vacante.confidencial

  return (
    <Card>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14 }}>
        La IA propone un texto por canal; edítalos antes de guardarlos.
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Button onClick={() => generar.mutate()} disabled={generar.isPending}>
          {generar.isPending ? 'Generando...' : Object.keys(textos).length ? 'Volver a generar con IA' : 'Generar textos con IA'}
        </Button>
        {borrador && (
          <>
            <Button variant="secondary" onClick={() => guardar.mutate()} disabled={guardar.isPending}>
              {guardar.isPending ? 'Guardando...' : 'Guardar textos'}
            </Button>
            <Button variant="ghost" onClick={() => setBorrador(null)}>Descartar cambios</Button>
          </>
        )}
      </div>

      {guardados.isLoading && <div style={{ padding: 20 }}><Spinner /></div>}
      {Object.keys(textos).length > 0 && (
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {Object.entries(textos).map(([canal, texto]) => (
            <div key={canal}>
              <label htmlFor={`texto-${canal}`} style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>
                {CANALES[canal] ?? canal}
              </label>
              <AreaTexto id={`texto-${canal}`} filas={canal === 'whatsapp' ? 3 : 6} valor={texto}
                onChange={(e) => setBorrador({ ...textos, [canal]: e.target.value })} />
            </div>
          ))}
        </div>
      )}

      <EnlacePostulacion vacante={vacante} />

      <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Feed XML para bolsas de empleo</p>
        {feedDisponible ? (
          <code style={{ display: 'block', padding: 10, background: 'var(--bg-page)', borderRadius: 6, fontSize: 12, color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
            {window.location.origin}/api/vacantes/{vacante.id}/feed-xml
          </code>
        ) : (
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Disponible cuando la vacante está abierta y no es confidencial.</p>
        )}
      </div>
    </Card>
  )
}

export default function VacanteDetalle() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [pestana, setPestana] = useState<Pestana>('info')
  const [confirmar, setConfirmar] = useState<'cerrar' | 'eliminar' | null>(null)

  const vacante = useQuery({
    queryKey: ['vacante', id],
    queryFn: async () => datos(await api.GET('/api/vacantes/{vacante_id}', { params: { path: { vacante_id: id } } }), 'No se encontró la vacante'),
  })
  const areas = useQuery({ queryKey: ['areas'], queryFn: async () => datos(await api.GET('/api/areas')) })

  const opciones = { params: { path: { vacante_id: id } } }
  const refrescar = () => {
    queryClient.invalidateQueries({ queryKey: ['vacante', id] })
    queryClient.invalidateQueries({ queryKey: ['vacantes'] })
  }

  const cambiarEstado = useMutation({
    mutationFn: async (accion: Accion) => {
      if (accion === 'publicar') return datos(await api.POST('/api/vacantes/{vacante_id}/publicar', opciones))
      if (accion === 'pausar') return datos(await api.POST('/api/vacantes/{vacante_id}/pausar', opciones))
      return datos(await api.POST('/api/vacantes/{vacante_id}/cerrar', opciones))
    },
    onSuccess: (_v, accion) => {
      toast.success(MENSAJE_ACCION[accion])
      refrescar()
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo cambiar el estado')),
    onSettled: () => setConfirmar(null),
  })

  const duplicar = useMutation({
    mutationFn: async () => datos(await api.POST('/api/vacantes/{vacante_id}/duplicar', opciones)),
    onSuccess: (copia) => {
      toast.success(`Copia creada en borrador: ${copia.codigo}`)
      queryClient.invalidateQueries({ queryKey: ['vacantes'] })
      navigate(`/vacantes/${copia.id}`)
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo duplicar')),
  })

  const eliminar = useMutation({
    mutationFn: async () => datos(await api.DELETE('/api/vacantes/{vacante_id}', opciones)),
    onSuccess: () => {
      toast.success('Vacante eliminada')
      queryClient.invalidateQueries({ queryKey: ['vacantes'] })
      navigate('/vacantes', { replace: true })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo eliminar')),
    onSettled: () => setConfirmar(null),
  })

  if (vacante.isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
  if (!vacante.data) {
    return (
      <div style={{ padding: '20px 24px' }}>
        <Volver onClick={() => navigate('/vacantes')}>Volver a vacantes</Volver>
        <EmptyState title="No se encontró la vacante" description={mensajeDe(vacante.error, '')} />
      </div>
    )
  }

  const v = vacante.data
  const area = areas.data?.find((a) => a.id === v.area_id)
  const ubicacion = [v.codigo, area?.nombre, v.ciudad, etiquetaDe(MODALIDADES, v.modalidad)].filter(Boolean).join(' · ')

  return (
    <div style={{ padding: '20px 24px', maxWidth: 960 }}>
      <Volver onClick={() => navigate('/vacantes')}>Volver a vacantes</Volver>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{v.titulo}</h1>
            <Badge variant={ESTADOS[v.estado].variante}>{ESTADOS[v.estado].etiqueta}</Badge>
            {v.confidencial && <Badge variant="info">Confidencial</Badge>}
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{ubicacion}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button variant="secondary" onClick={() => navigate(`/vacantes/${id}/editar`)}>Editar</Button>
          {(v.estado === 'borrador' || v.estado === 'pausada') && (
            <Button onClick={() => cambiarEstado.mutate('publicar')} disabled={cambiarEstado.isPending}>
              {v.estado === 'pausada' ? 'Reactivar' : 'Publicar'}
            </Button>
          )}
          {v.estado === 'abierta' && (
            <Button variant="secondary" onClick={() => cambiarEstado.mutate('pausar')} disabled={cambiarEstado.isPending}>Pausar</Button>
          )}
          {(v.estado === 'abierta' || v.estado === 'pausada') && (
            <Button variant="danger" onClick={() => setConfirmar('cerrar')}>Cerrar</Button>
          )}
          <Button variant="secondary" onClick={() => duplicar.mutate()} disabled={duplicar.isPending}>
            {duplicar.isPending ? 'Duplicando...' : 'Duplicar'}
          </Button>
          {v.estado === 'borrador' && <Button variant="ghost" onClick={() => setConfirmar('eliminar')}>Eliminar</Button>}
        </div>
      </div>

      <Pestanas actual={pestana} opciones={PESTANAS} onCambio={setPestana} />

      <motion.div key={pestana} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>
        {pestana === 'info' && <Informacion vacante={v} />}
        {pestana === 'candidatos' && <Candidatos vacante={v} />}
        {pestana === 'publicacion' && <Publicacion vacante={v} />}
      </motion.div>

      <ConfirmModal
        abierto={confirmar !== null}
        titulo={confirmar === 'eliminar' ? '¿Eliminar esta vacante?' : '¿Cerrar esta vacante?'}
        textoConfirmar={confirmar === 'eliminar' ? 'Eliminar' : 'Cerrar vacante'}
        peligroso
        procesando={cambiarEstado.isPending || eliminar.isPending}
        onConfirmar={() => (confirmar === 'eliminar' ? eliminar.mutate() : cambiarEstado.mutate('cerrar'))}
        onCancelar={() => setConfirmar(null)}
      >
        {confirmar === 'eliminar'
          ? 'Se elimina el borrador. Esta acción no se puede deshacer.'
          : 'Ya no recibirá postulaciones. Una vacante cerrada no se reabre: para volver a publicarla, duplícala.'}
      </ConfirmModal>
    </div>
  )
}
