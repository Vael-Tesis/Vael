import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { Iniciales } from '../../components/ui/Candidato'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import { Selector } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { ESTADOS_CANDIDATO } from './candidatosComun'
import PanelDecision, { AvisoSupervision } from './PanelDecision'

/**
 * P-10 Ranking (HU-17, HU-18; RF-A-14, RF-A-15): candidatos de una vacante ordenados por
 * score_final (DEC-007) con el desglose de CV, examen y entrevista; los procesos incompletos
 * aparecen aparte. La recomendación de finalistas (DEC-022, top_candidatos_finalistas) se
 * decide individual o en lote por el mismo endpoint de decisiones que la bandeja (DEC-009).
 */

function ScoreBar({ value, max = 20 }: { value: number | null; max?: number }) {
  const pct = Math.round(((value ?? 0) / max) * 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--bg-page)', borderRadius: 999, overflow: 'hidden' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ height: '100%', background: 'var(--text-primary)', borderRadius: 999 }}
        />
      </div>
      <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', minWidth: 28 }}>
        {value != null ? value.toFixed(1) : '—'}
      </span>
    </div>
  )
}

const COLUMNAS = '32px 1fr 110px 110px 110px 90px 140px 140px'

export default function Ranking() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [vacanteId, setVacanteId] = useState('')
  const [abierto, setAbierto] = useState<string | null>(null)
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set())
  const [confirmarLote, setConfirmarLote] = useState(false)
  const [revisionLote] = useState(() => new Date().toISOString())

  const vacantes = useQuery({ queryKey: ['vacantes', 'todas'], queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })) })
  const ranking = useQuery({
    queryKey: ['ranking', vacanteId],
    queryFn: async () => datos(await api.GET('/api/candidatos/ranking', { params: { query: { vacante_id: vacanteId } } }), 'No se pudo cargar el ranking'),
    enabled: vacanteId !== '',
  })

  const candidatos = ranking.data ?? []
  const completos = candidatos.filter((c) => c.proceso_completo)
  const incompletos = candidatos.filter((c) => !c.proceso_completo)
  const decidibles = completos.filter((c) => c.estado === 'entrevista_realizada')
  const seleccionados = decidibles.filter((c) => seleccion.has(c.id) && c.recomendacion_finalista !== null)

  const lote = useMutation({
    mutationFn: async () =>
      datos(
        await api.POST('/api/candidatos/decisiones/lote', {
          body: {
            etapa: 'entrevista',
            revision_inicio: revisionLote,
            decisiones: seleccionados.map((c) => ({ candidato_id: c.id, decision: c.recomendacion_finalista ?? 'avanzar' })),
          },
        }),
        'No se pudo confirmar el lote',
      ),
    onSuccess: (filas) => {
      toast.success(`${filas.length} decisiones de finalistas confirmadas`)
      setSeleccion(new Set())
      queryClient.invalidateQueries({ queryKey: ['ranking'] })
      queryClient.invalidateQueries({ queryKey: ['candidatos'] })
      queryClient.invalidateQueries({ queryKey: ['bandeja'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo confirmar el lote')),
    onSettled: () => setConfirmarLote(false),
  })

  function alternar(id: string) {
    setSeleccion((actual) => {
      const nueva = new Set(actual)
      if (nueva.has(id)) nueva.delete(id)
      else nueva.add(id)
      return nueva
    })
  }

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1100 }}>
      <PageHeader
        title="Ranking"
        description="Candidatos de la vacante ordenados por score final ponderado (DEC-007)"
        action={
          <Button onClick={() => setConfirmarLote(true)} disabled={seleccionados.length === 0 || lote.isPending}>
            Confirmar {seleccionados.length || ''} finalistas
          </Button>
        }
      />
      <div style={{ marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <AvisoSupervision />
        <div style={{ maxWidth: 320 }}>
          <Selector
            valor={vacanteId}
            onCambio={(v) => { setVacanteId(v); setSeleccion(new Set()); setAbierto(null) }}
            opciones={[{ valor: '', etiqueta: 'Selecciona una vacante' }, ...(vacantes.data ?? []).map((v) => ({ valor: v.id, etiqueta: v.titulo }))]}
          />
        </div>
      </div>

      {vacanteId === '' ? (
        <Card><EmptyState title="Selecciona una vacante" description="El ranking se calcula por vacante" /></Card>
      ) : ranking.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : ranking.error ? (
        <Card><EmptyState title="No se pudo cargar el ranking" description={mensajeDe(ranking.error, 'Intenta de nuevo')} /></Card>
      ) : candidatos.length === 0 ? (
        <Card><EmptyState title="Sin candidatos" description="Esta vacante todavía no tiene candidatos" /></Card>
      ) : (
        <>
          <Card padding="0">
            <div style={{
              display: 'grid', gridTemplateColumns: COLUMNAS, padding: '8px 16px',
              borderBottom: '1px solid var(--border)', fontSize: 11, fontWeight: 500,
              color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', gap: 12,
            }}>
              <span>#</span>
              <span>Candidato</span>
              <span>Score CV (20%)</span>
              <span>Examen (40%)</span>
              <span>Entrevista (40%)</span>
              <span style={{ textAlign: 'center' }}>Score final</span>
              <span>Recomendación</span>
              <span>Acciones</span>
            </div>

            {completos.length === 0 ? (
              <EmptyState title="Sin procesos completos" description="Todavía no hay candidatos con las tres notas" />
            ) : (
              completos.map((c, i) => {
                const expandido = abierto === c.id
                const puedeDecidir = c.estado === 'entrevista_realizada'
                return (
                  <div key={c.id}>
                    <motion.div
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03 }}
                      style={{ display: 'grid', gridTemplateColumns: COLUMNAS, padding: '12px 16px', borderBottom: '1px solid var(--border)', alignItems: 'center', gap: 12 }}
                    >
                      <span style={{ fontSize: 13, fontWeight: 600, color: i === 0 ? 'var(--warning-text)' : i === 1 ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
                        {i + 1}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                        {puedeDecidir && (
                          <input
                            type="checkbox"
                            aria-label={`Seleccionar a ${c.nombre} ${c.apellidos} para confirmar en lote`}
                            checked={seleccion.has(c.id)}
                            disabled={c.recomendacion_finalista === null}
                            onChange={() => alternar(c.id)}
                          />
                        )}
                        <Iniciales nombre={c.nombre} apellidos={c.apellidos} tamano={28} />
                        <div style={{ minWidth: 0 }}>
                          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{c.nombre} {c.apellidos}</p>
                          <Badge variant={ESTADOS_CANDIDATO[c.estado].variante}>{ESTADOS_CANDIDATO[c.estado].etiqueta}</Badge>
                        </div>
                      </div>
                      <ScoreBar value={c.score_cv != null ? c.score_cv / 5 : null} />
                      <ScoreBar value={c.nota_examen ?? null} />
                      <ScoreBar value={c.nota_entrevista ?? null} />
                      <div style={{ textAlign: 'center' }}>
                        <span style={{ fontSize: 15, fontWeight: 600, color: i === 0 ? 'var(--success-text)' : 'var(--text-primary)' }}>
                          {c.score_final != null ? c.score_final.toFixed(2) : '—'}
                        </span>
                      </div>
                      <div>
                        {c.recomendacion_finalista ? (
                          <Badge variant={c.recomendacion_finalista === 'avanzar' ? 'success' : 'danger'}>
                            {c.recomendacion_finalista === 'avanzar' ? 'Finalista' : 'Fuera del corte'}
                          </Badge>
                        ) : (
                          <Badge variant="neutral">—</Badge>
                        )}
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {puedeDecidir ? (
                          <Button size="sm" variant={expandido ? 'secondary' : 'primary'} onClick={() => setAbierto(expandido ? null : c.id)}>
                            {expandido ? 'Cerrar' : 'Decidir'}
                          </Button>
                        ) : (
                          <Button size="sm" variant="ghost" onClick={() => navigate(`/candidatos/${c.id}`)}>Detalle</Button>
                        )}
                      </div>
                    </motion.div>
                    <AnimatePresence>
                      {expandido && puedeDecidir && (
                        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} style={{ overflow: 'hidden' }}>
                          <div style={{ padding: '0 16px 16px', borderBottom: '1px solid var(--border)' }}>
                            <PanelDecision
                              candidatoId={c.id}
                              etapa="entrevista"
                              recomendacion={{
                                recomendacion_ia: c.recomendacion_finalista ?? null,
                                puntaje: c.score_final,
                                umbral: null,
                                justificacion_ia: null,
                              }}
                              onDecidido={() => setAbierto(null)}
                            />
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )
              })
            )}
          </Card>

          {incompletos.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                Procesos incompletos ({incompletos.length})
              </h3>
              <Card padding="0">
                {incompletos.map((c) => (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
                    <Iniciales nombre={c.nombre} apellidos={c.apellidos} tamano={28} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{c.nombre} {c.apellidos}</p>
                    </div>
                    <Badge variant={ESTADOS_CANDIDATO[c.estado].variante}>{ESTADOS_CANDIDATO[c.estado].etiqueta}</Badge>
                    <Button size="sm" variant="ghost" onClick={() => navigate(`/candidatos/${c.id}`)}>Detalle</Button>
                  </div>
                ))}
              </Card>
            </div>
          )}
        </>
      )}

      <ConfirmModal
        abierto={confirmarLote}
        titulo={`¿Confirmar ${seleccionados.length} decisiones de finalistas?`}
        textoConfirmar="Confirmar"
        procesando={lote.isPending}
        onConfirmar={() => lote.mutate()}
        onCancelar={() => setConfirmarLote(false)}
      >
        Cada candidato seleccionado recibe la decisión que coincide con el ranking: finalista o un único correo de
        cierre. Para decidir en contra del ranking, revisa al candidato de forma individual.
      </ConfirmModal>
    </div>
  )
}
