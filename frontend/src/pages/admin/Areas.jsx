import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Button from '../../components/ui/Button.jsx'

const DEMO = [
  { id: '1', nombre: 'Tecnología', codigo_corto: 'TI', activa: true, _count: { vacantes: 3 } },
  { id: '2', nombre: 'Diseño', codigo_corto: 'DIS', activa: true, _count: { vacantes: 1 } },
  { id: '3', nombre: 'Comercial', codigo_corto: 'COM', activa: true, _count: { vacantes: 1 } },
  { id: '4', nombre: 'Recursos Humanos', codigo_corto: 'RRHH', activa: true, _count: { vacantes: 0 } },
  { id: '5', nombre: 'Finanzas', codigo_corto: 'FIN', activa: false, _count: { vacantes: 0 } },
]

export default function Areas() {
  const { data } = useQuery({
    queryKey: ['areas'],
    queryFn: () => api.get('/areas').then(r => r.data).catch(() => DEMO),
  })

  const areas = data || DEMO

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Áreas"
        description="Áreas organizacionales de la empresa"
        action={<Button>+ Nueva área</Button>}
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        {areas.map((a, i) => (
          <motion.div key={a.id}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <Card>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: 8,
                  background: 'var(--bg-page)',
                  border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)',
                }}>
                  {a.codigo_corto}
                </div>
                <Badge variant={a.activa ? 'success' : 'neutral'}>
                  {a.activa ? 'Activa' : 'Inactiva'}
                </Badge>
              </div>
              <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>
                {a.nombre}
              </p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {a._count?.vacantes || 0} vacante{a._count?.vacantes !== 1 ? 's' : ''} activa{a._count?.vacantes !== 1 ? 's' : ''}
              </p>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}