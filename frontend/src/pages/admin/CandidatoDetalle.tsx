import { useState, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import { puedeDecidir } from '../../auth/permisos'
import { usuarioActual } from '../../auth/sesion'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { Iniciales, PuntajeCv } from '../../components/ui/Candidato'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import { AreaTexto, Pestanas, Selector, Volver, estiloControl, type Opcion } from '../../components/ui/Formulario'
import Spinner from '../../components/ui/Spinner'
import { CLASIFICACIONES, ESTADOS_CANDIDATO, type EstadoCandidato } from './candidatosComun'
import PanelDecision, { AvisoSupervision, ETAPAS, type Etapa, type Recomendacion } from './PanelDecision'

/**
 * P-08 Detalle de candidato (HU-12, HU-13, HU-16): análisis de la IA (sin datos de
 * emociones, DEC-001), evaluaciones, notas propias editables, etiquetas e historial de
 * decisiones. Las acciones de avance y descarte pasan por el endpoint de decisiones (DEC-009).
 */

type Detalle = Esquemas['CandidatoDetalleResponse']
type Nota = Esquemas['NotaResponse']
type Pestana = 'analisis' | 'evaluaciones' | 'notas' | 'etiquetas' | 'historial'

const PESTANAS: readonly Opcion<Pestana>[] = [
  { valor: 'analisis', etiqueta: 'Análisis de la IA' },
  { valor: 'evaluaciones', etiqueta: 'Evaluaciones' },
  { valor: 'notas', etiqueta: 'Notas' },
  { valor: 'etiquetas', etiqueta: 'Etiquetas' },
  { valor: 'historial', etiqueta: 'Historial de decisiones' },
]

const ETAPA_PENDIENTE: Partial<Record<EstadoCandidato, Etapa>> = {
  cv_por_confirmar: 'cv',
  examen_por_confirmar: 'examen',
  entrevista_realizada: 'entrevista',
}

const ESTADOS_CON_CORREO: readonly EstadoCandidato[] = [
  'cv_aprobado', 'examen_pendiente', 'examen_aprobado', 'entrevista_pendiente', 'finalista',
  'cv_rechazado', 'examen_rechazado', 'descartado',
]

const fecha = (valor: string) => new Date(valor.endsWith('Z') ? valor : `${valor}Z`).toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' })

function Titulo({ children }: { children: ReactNode }) {
  return <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{children}</p>
}

function Enlace({ etiqueta, url }: { etiqueta: string; url: string | null }) {
  return (
    <div>
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>{etiqueta}</p>
      {url ? (
        <a href={url.startsWith('http') ? url : `https://${url}`} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--brand)', wordBreak: 'break-all' }}>{url}</a>
      ) : (
        <p style={{ fontSize: 13, color: 'var(--text-primary)' }}>—</p>
      )}
    </div>
  )
}

function Analisis({ c }: { c: Detalle }) {
  return (
    <Card>
      {c.clasificacion_ia === null && c.score_cv === null ? (
        <EmptyState title="El CV aún no tiene análisis" description="Se muestra aquí cuando la IA termina" />
      ) : (
        <>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 16 }}>
            {c.clasificacion_ia && <Badge variant={CLASIFICACIONES[c.clasificacion_ia].variante}>{CLASIFICACIONES[c.clasificacion_ia].etiqueta}</Badge>}
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Puntaje de CV:</span> <PuntajeCv valor={c.score_cv} />
            {c.analizado_en && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Analizado el {fecha(c.analizado_en)}</span>}
          </div>
          {c.resumen_ia && (
            <div style={{ marginBottom: 18 }}>
              <Titulo>Resumen y justificación</Titulo>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{c.resumen_ia}</p>
            </div>
          )}
          {c.habilidades_detectadas.length > 0 && (
            <div style={{ marginBottom: 18 }}>
              <Titulo>Habilidades detectadas</Titulo>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>{c.habilidades_detectadas.map((h) => <Badge key={h} variant="info">{h}</Badge>)}</div>
            </div>
          )}
          {c.inconsistencias.length > 0 && (
            <div style={{ marginBottom: 18 }}>
              <Titulo>Inconsistencias</Titulo>
              <ul style={{ fontSize: 13, color: 'var(--warning-text)', paddingLeft: 18, lineHeight: 1.6 }}>{c.inconsistencias.map((i) => <li key={i}>{i}</li>)}</ul>
            </div>
          )}
        </>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
        <Enlace etiqueta="LinkedIn" url={c.linkedin} />
        <Enlace etiqueta="GitHub" url={c.github} />
        <Enlace etiqueta="Portafolio" url={c.portfolio} />
      </div>
    </Card>
  )
}

function Evaluaciones({ c }: { c: Detalle }) {
  const navigate = useNavigate()
  const examenes = useQuery({
    queryKey: ['candidato', c.id, 'examenes'],
    queryFn: async () => datos(await api.GET('/api/evaluaciones/examenes', { params: { query: { candidato_id: c.id } } })),
  })
  const entrevistas = useQuery({
    queryKey: ['candidato', c.id, 'entrevistas'],
    queryFn: async () => datos(await api.GET('/api/entrevista', { params: { query: { candidato_id: c.id } } })),
  })
  const examen = examenes.data?.[0]
  const entrevista = entrevistas.data?.[0]
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
      <Card>
        <Titulo>Examen técnico</Titulo>
        {examen ? (
          <>
            <p style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary)' }}>{examen.nota ?? '—'}<span style={{ fontSize: 13, color: 'var(--text-muted)' }}>/20</span></p>
            <div style={{ display: 'flex', gap: 6, margin: '8px 0 12px' }}>
              <Badge variant="neutral">{examen.estado}</Badge>
              <Badge variant={examen.semaforo === 'verde' ? 'success' : examen.semaforo === 'amarillo' ? 'warning' : 'danger'}>Integridad: {examen.semaforo}</Badge>
            </div>
            <Button size="sm" variant="secondary" onClick={() => navigate(`/examenes/${examen.id}`)}>Ver examen</Button>
          </>
        ) : <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin examen</p>}
      </Card>
      <Card>
        <Titulo>Entrevista con EVA</Titulo>
        {entrevista ? (
          <>
            <p style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary)' }}>{entrevista.nota ?? '—'}<span style={{ fontSize: 13, color: 'var(--text-muted)' }}>/20</span></p>
            <div style={{ margin: '8px 0 12px' }}><Badge variant="neutral">{entrevista.estado}</Badge></div>
            <Button size="sm" variant="secondary" onClick={() => navigate(`/entrevistas/${entrevista.id}`)}>Ver entrevista</Button>
          </>
        ) : <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin entrevista</p>}
      </Card>
      <Card>
        <Titulo>Puntaje final</Titulo>
        <p style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary)' }}>{c.score_final ?? '—'}<span style={{ fontSize: 13, color: 'var(--text-muted)' }}>/20</span></p>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>CV 20 % · examen 40 % · entrevista 40 % (DEC-007). Es una recomendación para el ranking.</p>
      </Card>
    </div>
  )
}

function Notas({ c }: { c: Detalle }) {
  const queryClient = useQueryClient()
  const yo = usuarioActual()
  const [nueva, setNueva] = useState('')
  const [editando, setEditando] = useState<{ id: string; contenido: string } | null>(null)
  const [porEliminar, setPorEliminar] = useState<Nota | null>(null)
  const ruta = { params: { path: { candidato_id: c.id } } }

  const notas = useQuery({
    queryKey: ['candidato', c.id, 'notas'],
    queryFn: async () => datos(await api.GET('/api/candidatos/{candidato_id}/notas', ruta)),
  })
  const refrescar = () => queryClient.invalidateQueries({ queryKey: ['candidato', c.id, 'notas'] })

  const crear = useMutation({
    mutationFn: async () => datos(await api.POST('/api/candidatos/{candidato_id}/notas', { ...ruta, body: { contenido: nueva.trim() } })),
    onSuccess: () => { setNueva(''); refrescar() },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo guardar la nota')),
  })
  const editar = useMutation({
    mutationFn: async (n: { id: string; contenido: string }) =>
      datos(await api.PUT('/api/candidatos/{candidato_id}/notas/{nota_id}', {
        params: { path: { candidato_id: c.id, nota_id: n.id } }, body: { contenido: n.contenido.trim() },
      })),
    onSuccess: () => { setEditando(null); refrescar() },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo editar la nota')),
  })
  const eliminar = useMutation({
    mutationFn: async (n: Nota) =>
      datos(await api.DELETE('/api/candidatos/{candidato_id}/notas/{nota_id}', { params: { path: { candidato_id: c.id, nota_id: n.id } } })),
    onSuccess: () => { toast.success('Nota eliminada'); refrescar() },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo eliminar la nota')),
    onSettled: () => setPorEliminar(null),
  })

  return (
    <Card>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>Notas internas: el candidato nunca las ve.</p>
      <AreaTexto valor={nueva} onChange={(e) => setNueva(e.target.value)} placeholder="Escribe una nota sobre el candidato" />
      <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '8px 0 16px' }}>
        <Button size="sm" onClick={() => crear.mutate()} disabled={nueva.trim() === '' || crear.isPending}>Agregar nota</Button>
      </div>
      {notas.data?.length === 0 && <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Aún no hay notas</p>}
      {notas.data?.map((n) => {
        const esMia = n.autor_id === yo?.id
        return (
          <div key={n.id} style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
            {editando?.id === n.id ? (
              <>
                <AreaTexto valor={editando.contenido} onChange={(e) => setEditando({ id: n.id, contenido: e.target.value })} />
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  <Button size="sm" onClick={() => editar.mutate(editando)} disabled={editando.contenido.trim() === '' || editar.isPending}>Guardar</Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditando(null)}>Cancelar</Button>
                </div>
              </>
            ) : (
              <>
                <p style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4, whiteSpace: 'pre-wrap' }}>{n.contenido}</p>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {n.autor_nombre ?? 'Usuario'} · {fecha(n.created_at)}{n.updated_at && ` · editada ${fecha(n.updated_at)}`}
                  </span>
                  {esMia && <Button size="sm" variant="ghost" onClick={() => setEditando({ id: n.id, contenido: n.contenido })}>Editar</Button>}
                  {(esMia || yo?.rol === 'admin') && <Button size="sm" variant="ghost" onClick={() => setPorEliminar(n)}>Eliminar</Button>}
                </div>
              </>
            )}
          </div>
        )
      })}
      <ConfirmModal abierto={porEliminar !== null} titulo="¿Eliminar esta nota?" textoConfirmar="Eliminar" peligroso
        procesando={eliminar.isPending} onConfirmar={() => porEliminar && eliminar.mutate(porEliminar)} onCancelar={() => setPorEliminar(null)} />
    </Card>
  )
}

function Etiquetas({ c }: { c: Detalle }) {
  const queryClient = useQueryClient()
  const [elegida, setElegida] = useState('')
  const [nueva, setNueva] = useState('')
  const todas = useQuery({ queryKey: ['tags'], queryFn: async () => datos(await api.GET('/api/tags')) })
  const asignadas = new Set(c.tags.map((t) => t.id))
  const disponibles = (todas.data ?? []).filter((t) => !asignadas.has(t.id))
  const refrescar = () => {
    queryClient.invalidateQueries({ queryKey: ['candidato', c.id] })
    queryClient.invalidateQueries({ queryKey: ['tags'] })
  }

  const asignar = useMutation({
    mutationFn: async (tagId: string) =>
      datos(await api.POST('/api/candidatos/{candidato_id}/tags', { params: { path: { candidato_id: c.id } }, body: { tag_id: tagId } })),
    onSuccess: () => { setElegida(''); refrescar() },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo asignar la etiqueta')),
  })
  const crearYAsignar = useMutation({
    mutationFn: async () => {
      const tag = datos(await api.POST('/api/tags', { body: { nombre: nueva.trim(), color: null } }), 'No se pudo crear la etiqueta')
      return datos(await api.POST('/api/candidatos/{candidato_id}/tags', { params: { path: { candidato_id: c.id } }, body: { tag_id: tag.id } }))
    },
    onSuccess: () => { setNueva(''); refrescar() },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo crear la etiqueta')),
  })
  const quitar = useMutation({
    mutationFn: async (tagId: string) =>
      datos(await api.DELETE('/api/candidatos/{candidato_id}/tags/{tag_id}', { params: { path: { candidato_id: c.id, tag_id: tagId } } })),
    onSuccess: refrescar,
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo quitar la etiqueta')),
  })

  return (
    <Card>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
        {c.tags.length === 0 && <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Sin etiquetas</p>}
        {c.tags.map((t) => (
          <span key={t.id} style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, padding: '3px 8px', borderRadius: 999,
            background: 'var(--brand-soft)', color: 'var(--brand)', border: t.color ? `1px solid ${t.color}` : 'none',
          }}>
            {t.nombre}
            <button type="button" aria-label={`Quitar ${t.nombre}`} onClick={() => quitar.mutate(t.id)}
              style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0 }}>×</button>
          </span>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <Selector valor={elegida} onCambio={setElegida}
            opciones={[{ valor: '', etiqueta: disponibles.length ? 'Agregar una etiqueta' : 'No hay más etiquetas' }, ...disponibles.map((t) => ({ valor: t.id, etiqueta: t.nombre }))]} />
          <Button size="sm" onClick={() => asignar.mutate(elegida)} disabled={elegida === '' || asignar.isPending}>Asignar</Button>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <input style={estiloControl} placeholder="Nueva etiqueta" aria-label="Nueva etiqueta" maxLength={50} value={nueva} onChange={(e) => setNueva(e.target.value)} />
          <Button size="sm" variant="secondary" onClick={() => crearYAsignar.mutate()} disabled={nueva.trim() === '' || crearYAsignar.isPending}>Crear</Button>
        </div>
      </div>
    </Card>
  )
}

function Historial({ c }: { c: Detalle }) {
  if (c.decisiones.length === 0) return <Card><EmptyState title="Sin decisiones registradas" description="Cada decisión de RRHH queda aquí y no se puede editar ni borrar" /></Card>
  const reemplazadas = new Set(c.decisiones.map((d) => d.reemplaza_a).filter(Boolean))
  return (
    <Card padding="0">
      {[...c.decisiones].reverse().map((d, i) => (
        <div key={d.id} style={{ padding: '12px 16px', borderTop: i ? '1px solid var(--border)' : 'none', opacity: reemplazadas.has(d.id) ? 0.6 : 1 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 6 }}>
            <Badge variant="neutral">{ETAPAS[d.etapa]}</Badge>
            <Badge variant={d.decision === 'avanzar' ? 'success' : 'danger'}>{d.decision === 'avanzar' ? 'Avanzó' : 'Descartado'}</Badge>
            {d.recomendacion_ia && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>IA: {d.recomendacion_ia}</span>}
            {d.coincide_con_ia === false && <Badge variant="warning">Contraria a la IA</Badge>}
            {d.reemplaza_a && <Badge variant="info">Revierte una decisión anterior</Badge>}
            {reemplazadas.has(d.id) && <Badge variant="neutral">Reemplazada</Badge>}
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {d.decidido_por_nombre ?? 'Usuario'} · {fecha(d.decidido_en)}
            {d.puntaje !== null && ` · puntaje ${d.puntaje}`}{d.umbral !== null && ` (umbral ${d.umbral})`}
          </p>
          {d.justificacion_humana && <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 6 }}>Justificación: {d.justificacion_humana}</p>}
        </div>
      ))}
    </Card>
  )
}

function DecisionPendiente({ c, etapa }: { c: Detalle; etapa: Etapa }) {
  const bandeja = useQuery({
    queryKey: ['bandeja', { vacante_id: c.vacante_id, etapa }],
    enabled: etapa !== 'entrevista',
    queryFn: async () =>
      datos(await api.GET('/api/candidatos/por-confirmar', { params: { query: { vacante_id: c.vacante_id, etapa } } })),
  })
  const recomendacion: Recomendacion | undefined =
    etapa === 'entrevista'
      ? { recomendacion_ia: null, puntaje: c.score_final, umbral: null, justificacion_ia: null }
      : bandeja.data?.find((i) => i.candidato.id === c.id)
  return (
    <Card style={{ marginBottom: 16, borderColor: 'var(--brand)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>Decisión pendiente: {ETAPAS[etapa]}</p>
        <AvisoSupervision />
      </div>
      {recomendacion ? <PanelDecision candidatoId={c.id} etapa={etapa} recomendacion={recomendacion} /> : <Spinner />}
    </Card>
  )
}

export default function CandidatoDetalle() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [pestana, setPestana] = useState<Pestana>('analisis')
  const ruta = { params: { path: { candidato_id: id } } }

  const candidato = useQuery({
    queryKey: ['candidato', id],
    queryFn: async () => datos(await api.GET('/api/candidatos/{candidato_id}', ruta), 'No se encontró el candidato'),
  })
  const vacantes = useQuery({ queryKey: ['vacantes', 'todas'], queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })) })

  const reanalizar = useMutation({
    mutationFn: async () => datos(await api.POST('/api/candidatos/{candidato_id}/analizar', ruta)),
    onSuccess: () => { toast.success('Análisis de CV en curso'); queryClient.invalidateQueries({ queryKey: ['candidato', id] }) },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo iniciar el análisis')),
  })
  const reenviar = useMutation({
    mutationFn: async () => datos(await api.POST('/api/candidatos/{candidato_id}/reenviar-correo-etapa', ruta)),
    onSuccess: () => toast.success('Correo reenviado'),
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo reenviar el correo')),
  })
  const contratar = useMutation({
    mutationFn: async () => datos(await api.POST('/api/candidatos/{candidato_id}/cambiar-estado', { ...ruta, body: { estado: 'contratado' } })),
    onSuccess: () => { toast.success('Candidato marcado como contratado'); queryClient.invalidateQueries({ queryKey: ['candidato', id] }) },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo actualizar el estado')),
  })
  const enviarBanco = useMutation({
    mutationFn: async () => datos(await api.POST('/api/candidatos/{candidato_id}/banco-talento', ruta)),
    onSuccess: () => { toast.success('Candidato enviado al banco de talento'); queryClient.invalidateQueries({ queryKey: ['candidato', id] }) },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo enviar al banco de talento')),
  })

  if (candidato.isLoading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
  if (!candidato.data) {
    return (
      <div style={{ padding: '20px 24px' }}>
        <Volver onClick={() => navigate('/candidatos')}>Volver a candidatos</Volver>
        <EmptyState title="No se encontró el candidato" description={mensajeDe(candidato.error, '')} />
      </div>
    )
  }

  const c = candidato.data
  const rol = usuarioActual()?.rol
  const etapaPendiente = ETAPA_PENDIENTE[c.estado]
  const vacante = vacantes.data?.find((v) => v.id === c.vacante_id)

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1000 }}>
      <Volver onClick={() => navigate('/candidatos')}>Volver a candidatos</Volver>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', minWidth: 0 }}>
          <Iniciales nombre={c.nombre} apellidos={c.apellidos} tamano={44} />
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{c.nombre} {c.apellidos}</h1>
              <Badge variant={ESTADOS_CANDIDATO[c.estado].variante}>{ESTADOS_CANDIDATO[c.estado].etiqueta}</Badge>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {c.email}{c.telefono && ` · ${c.telefono}`} · {vacante ? `${vacante.titulo} (${vacante.codigo})` : 'Vacante'}
            </p>
          </div>
        </div>
        {puedeDecidir(rol) && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(c.estado === 'postulado' || c.estado === 'cv_por_confirmar') && (
              <Button variant="secondary" onClick={() => reanalizar.mutate()} disabled={reanalizar.isPending}>Reanalizar CV</Button>
            )}
            {ESTADOS_CON_CORREO.includes(c.estado) && (
              <Button variant="secondary" onClick={() => reenviar.mutate()} disabled={reenviar.isPending}>Reenviar correo de la etapa</Button>
            )}
            {c.estado === 'finalista' && (
              <Button onClick={() => contratar.mutate()} disabled={contratar.isPending}>Marcar como contratado</Button>
            )}
            {c.en_banco_talento ? (
              <Badge variant="info">En el banco de talento</Badge>
            ) : (
              <Button variant="secondary" onClick={() => enviarBanco.mutate()} disabled={enviarBanco.isPending}>Enviar al banco de talento</Button>
            )}
          </div>
        )}
      </div>

      {etapaPendiente && puedeDecidir(rol) && <DecisionPendiente key={`${c.id}-${etapaPendiente}`} c={c} etapa={etapaPendiente} />}

      <Pestanas actual={pestana} opciones={PESTANAS} onCambio={setPestana} />
      <motion.div key={pestana} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>
        {pestana === 'analisis' && <Analisis c={c} />}
        {pestana === 'evaluaciones' && <Evaluaciones c={c} />}
        {pestana === 'notas' && <Notas c={c} />}
        {pestana === 'etiquetas' && <Etiquetas c={c} />}
        {pestana === 'historial' && <Historial c={c} />}
      </motion.div>
    </div>
  )
}
