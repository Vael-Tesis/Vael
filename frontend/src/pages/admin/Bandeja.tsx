import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { Iniciales } from '../../components/ui/Candidato'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import { Filtros, Selector, type Opcion } from '../../components/ui/Formulario'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import PanelDecision, { AvisoSupervision, ETAPAS, ResumenRecomendacion, type Etapa } from './PanelDecision'

/**
 * P-09 Bandeja de recomendaciones (HU-15, RF-A-11; requisitos del doc 15): filtros por
 * vacante y etapa; por candidato, puntaje, umbral, recomendación, justificación y, en examen,
 * semáforo; confirmar o decidir lo contrario con justificación; lote solo de coincidencias.
 */

type Item = Esquemas['RecomendacionPendienteResponse']
type FiltroEtapa = 'cv' | 'examen' | 'todas'

const FILTROS: readonly Opcion<FiltroEtapa>[] = [
  { valor: 'todas', etiqueta: 'CV y examen' },
  { valor: 'cv', etiqueta: 'CV' },
  { valor: 'examen', etiqueta: 'Examen' },
]

export default function Bandeja() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [vacanteId, setVacanteId] = useState('')
  const [etapa, setEtapa] = useState<FiltroEtapa>('todas')
  const [abierto, setAbierto] = useState<string | null>(null)
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set())
  const [confirmarLote, setConfirmarLote] = useState(false)
  const [revisionLote] = useState(() => new Date().toISOString())

  const query = { ...(vacanteId ? { vacante_id: vacanteId } : {}), ...(etapa !== 'todas' ? { etapa } : {}) }
  const bandeja = useQuery({
    queryKey: ['bandeja', query],
    queryFn: async () => datos(await api.GET('/api/candidatos/por-confirmar', { params: { query } }), 'No se pudo cargar la bandeja'),
  })
  const vacantes = useQuery({ queryKey: ['vacantes', 'todas'], queryFn: async () => datos(await api.GET('/api/vacantes', { params: { query: {} } })) })
  const tituloVacante = new Map((vacantes.data ?? []).map((v) => [v.id, v.titulo]))

  const items = bandeja.data ?? []
  const elegibles = items.filter((i) => i.recomendacion_ia !== null)
  const seleccionados = elegibles.filter((i) => seleccion.has(i.candidato.id))

  const lote = useMutation({
    mutationFn: async () => {
      // El lote es por etapa (DEC-009): una llamada por cada etapa seleccionada
      const porEtapa = new Map<Etapa, Item[]>()
      for (const item of seleccionados) porEtapa.set(item.etapa, [...(porEtapa.get(item.etapa) ?? []), item])
      let total = 0
      for (const [etapaLote, grupo] of porEtapa) {
        const filas = datos(
          await api.POST('/api/candidatos/decisiones/lote', {
            body: {
              etapa: etapaLote,
              revision_inicio: revisionLote,
              decisiones: grupo.map((i) => ({ candidato_id: i.candidato.id, decision: i.recomendacion_ia ?? 'avanzar' })),
            },
          }),
          'No se pudo confirmar el lote',
        )
        total += filas.length
      }
      return total
    },
    onSuccess: (total) => {
      toast.success(`${total} recomendaciones confirmadas`)
      setSeleccion(new Set())
      queryClient.invalidateQueries({ queryKey: ['bandeja'] })
      queryClient.invalidateQueries({ queryKey: ['candidatos'] })
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
    <div style={{ padding: '20px 24px', maxWidth: 1000 }}>
      <PageHeader
        title="Bandeja de recomendaciones"
        description="Candidatos que esperan tu decisión en las etapas de CV y examen"
        action={
          <Button onClick={() => setConfirmarLote(true)} disabled={seleccionados.length === 0 || lote.isPending}>
            Confirmar {seleccionados.length || ''} seleccionadas
          </Button>
        }
      />
      <div style={{ marginBottom: 14 }}><AvisoSupervision /></div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Filtros actual={etapa} opciones={FILTROS} onCambio={(v) => { setEtapa(v); setSeleccion(new Set()) }} />
        <div style={{ minWidth: 220, flex: '0 1 300px' }}>
          <Selector valor={vacanteId} onCambio={(v) => { setVacanteId(v); setSeleccion(new Set()) }}
            opciones={[{ valor: '', etiqueta: 'Todas las vacantes' }, ...(vacantes.data ?? []).map((v) => ({ valor: v.id, etiqueta: v.titulo }))]} />
        </div>
      </div>

      {bandeja.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : bandeja.error ? (
        <Card><EmptyState title="No se pudo cargar la bandeja" description={mensajeDe(bandeja.error, 'Intenta de nuevo')} /></Card>
      ) : items.length === 0 ? (
        <Card><EmptyState title="No hay recomendaciones pendientes" description="Cuando la IA termine un análisis, aparecerá aquí para tu decisión" /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map((item) => {
            const { candidato } = item
            const expandido = abierto === candidato.id
            return (
              <Card key={candidato.id} style={{ padding: '12px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <input
                    type="checkbox"
                    aria-label={`Seleccionar a ${candidato.nombre} ${candidato.apellidos} para confirmar en lote`}
                    checked={seleccion.has(candidato.id)}
                    disabled={item.recomendacion_ia === null}
                    onChange={() => alternar(candidato.id)}
                  />
                  <Iniciales nombre={candidato.nombre} apellidos={candidato.apellidos} />
                  <div style={{ flex: '1 1 200px', minWidth: 0 }}>
                    <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{candidato.nombre} {candidato.apellidos}</p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {ETAPAS[item.etapa]} · {tituloVacante.get(candidato.vacante_id) ?? 'Vacante'}
                    </p>
                  </div>
                  <ResumenRecomendacion etapa={item.etapa} recomendacion={item} />
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Button size="sm" variant={expandido ? 'secondary' : 'primary'} onClick={() => setAbierto(expandido ? null : candidato.id)}>
                      {expandido ? 'Cerrar' : 'Revisar'}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => navigate(`/candidatos/${candidato.id}`)}>Detalle</Button>
                  </div>
                </div>
                <AnimatePresence>
                  {expandido && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                      style={{ overflow: 'hidden' }}>
                      <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                        <PanelDecision candidatoId={candidato.id} etapa={item.etapa} recomendacion={item} onDecidido={() => setAbierto(null)} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )
          })}
        </div>
      )}

      <ConfirmModal
        abierto={confirmarLote}
        titulo={`¿Confirmar ${seleccionados.length} recomendaciones de la IA?`}
        textoConfirmar="Confirmar"
        procesando={lote.isPending}
        onConfirmar={() => lote.mutate()}
        onCancelar={() => setConfirmarLote(false)}
      >
        Cada candidato recibirá el correo que corresponde a la recomendación confirmada: el de la etapa siguiente si
        avanza, o un único correo de cierre si se descarta. Para decidir en contra de la IA, revisa al candidato de
        forma individual.
      </ConfirmModal>
    </div>
  )
}
