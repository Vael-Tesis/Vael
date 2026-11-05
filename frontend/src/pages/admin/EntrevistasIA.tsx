import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { api, datos, mensajeDe } from '../../api/cliente'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'
import { nombreCompleto, useCandidatos, useVacantes, varianteEstadoEntrevista } from './evaluacionesComun'

/**
 * P-13 Entrevistas (HU-19, RF-A-16): resultados de las entrevistas conducidas por EVA.
 * Usa el cliente tipado contra `GET /api/entrevista` (la ruta real); el `.jsx` anterior
 * llamaba a `/entrevista/lista`, que no existe (doc 06, doc 15 V-16). El listado no trae
 * `dimensiones_json` (solo el detalle, `GET /entrevista/detalle/{id}`).
 */

export default function EntrevistasIA() {
  const navigate = useNavigate()
  const entrevistas = useQuery({
    queryKey: ['entrevistas'],
    queryFn: async () => datos(await api.GET('/api/entrevista', { params: { query: {} } }), 'No se pudieron cargar las entrevistas'),
  })
  const candidatos = useCandidatos()
  const vacantes = useVacantes()

  const candidatoPorId = new Map((candidatos.data ?? []).map((c) => [c.id, c]))
  const tituloVacante = new Map((vacantes.data ?? []).map((v) => [v.id, v.titulo]))

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader title="Entrevistas IA" description="Resultados de entrevistas conducidas por EVA" />

      {entrevistas.isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
      ) : entrevistas.error ? (
        <Card><EmptyState title="No se pudieron cargar las entrevistas" description={mensajeDe(entrevistas.error, 'Intenta de nuevo')} /></Card>
      ) : (entrevistas.data ?? []).length === 0 ? (
        <Card><EmptyState title="Sin entrevistas" /></Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(entrevistas.data ?? []).map((e, i) => (
            <motion.div key={e.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{nombreCompleto(candidatoPorId.get(e.candidato_id))}</p>
                      <Badge variant={varianteEstadoEntrevista(e.estado)}>{e.estado}</Badge>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
                      {tituloVacante.get(e.vacante_id) ?? 'Vacante'}
                      {e.duracion_minutos && ` · ${e.duracion_minutos} min`}
                    </p>
                    <button onClick={() => navigate(`/entrevistas/${e.id}`)} style={{
                      background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 12px',
                      fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer',
                    }}>Ver detalle completo</button>
                  </div>
                  <div style={{ textAlign: 'center', flexShrink: 0 }}>
                    <p style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-1px', color: e.nota != null ? (e.nota >= 13 ? 'var(--success-text)' : 'var(--danger-text)') : 'var(--text-muted)' }}>
                      {e.nota != null ? e.nota.toFixed(1) : '—'}
                    </p>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>/ 20</p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
