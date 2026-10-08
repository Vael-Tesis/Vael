import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import api from '../../services/api.js'
import PageHeader from '../../components/ui/PageHeader.jsx'
import Card from '../../components/ui/Card.jsx'
import Badge from '../../components/ui/Badge.jsx'
import Button from '../../components/ui/Button.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'

const DEMO = [
  { id: '1', nombre: 'Gabriel', apellidos: 'Llanos', email: 'gabriel@empresa.com', rol: 'admin', activo: true },
  { id: '2', nombre: 'Diego', apellidos: 'Nina', email: 'diego@empresa.com', rol: 'reclutador', activo: true },
  { id: '3', nombre: 'Ana', apellidos: 'García', email: 'ana@empresa.com', rol: 'evaluador', activo: true },
  { id: '4', nombre: 'Luis', apellidos: 'Mendoza', email: 'luis@empresa.com', rol: 'gerente', activo: false },
]

const ROL_VARIANT = {
  admin:      'danger',
  reclutador: 'info',
  evaluador:  'warning',
  gerente:    'neutral',
}

export default function Usuarios() {
  const { data } = useQuery({
    queryKey: ['usuarios'],
    queryFn: () => api.get('/auth/usuarios').then(r => r.data).catch(() => DEMO),
  })

  const usuarios = data || DEMO

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Usuarios"
        description="Equipo RRHH con acceso al sistema"
        action={<Button>+ Nuevo usuario</Button>}
      />

      <Card padding="0">
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 180px 100px 80px 80px',
          padding: '8px 16px', borderBottom: '1px solid var(--border)',
          fontSize: 11, fontWeight: 500, color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.05em', gap: 12,
        }}>
          <span>Usuario</span>
          <span>Email</span>
          <span>Rol</span>
          <span>Estado</span>
          <span></span>
        </div>

        {usuarios.length === 0 ? <EmptyState title="Sin usuarios" /> : (
          usuarios.map((u, i) => (
            <motion.div key={u.id}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: i * 0.04 }}
              style={{
                display: 'grid', gridTemplateColumns: '1fr 180px 100px 80px 80px',
                padding: '10px 16px', borderBottom: '1px solid var(--border)',
                alignItems: 'center', gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 30, height: 30, borderRadius: '50%',
                  background: 'var(--bg-page)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)', flexShrink: 0,
                }}>
                  {u.nombre[0]}{u.apellidos[0]}
                </div>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                  {u.nombre} {u.apellidos}
                </p>
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.email}</span>
              <Badge variant={ROL_VARIANT[u.rol] || 'neutral'}>{u.rol}</Badge>
              <Badge variant={u.activo ? 'success' : 'neutral'}>
                {u.activo ? 'Activo' : 'Inactivo'}
              </Badge>
              <Button variant="ghost" size="sm">···</Button>
            </motion.div>
          ))
        )}
      </Card>
    </div>
  )
}