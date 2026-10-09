import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import { sinBackend } from '../../utils/devFallback.js'
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

function MenuUsuario({ usuario, abierto, onToggle, onActivar, onDesactivar, onCambiarPassword }) {
  return (
    <div style={{ position: 'relative' }}>
      <Button variant="ghost" size="sm" onClick={onToggle}>···</Button>
      {abierto && (
        <>
          <div onClick={onToggle} style={{ position: 'fixed', inset: 0, zIndex: 9 }} />
          <div style={{
            position: 'absolute', right: 0, top: '100%', marginTop: 4, zIndex: 10,
            background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)', minWidth: 180, overflow: 'hidden',
          }}>
            {usuario.activo ? (
              <button onClick={onDesactivar} style={menuItemStyle}>Desactivar usuario</button>
            ) : (
              <button onClick={onActivar} style={menuItemStyle}>Activar usuario</button>
            )}
            <button onClick={onCambiarPassword} style={menuItemStyle}>Cambiar contraseña</button>
          </div>
        </>
      )}
    </div>
  )
}

const menuItemStyle = {
  display: 'block', width: '100%', textAlign: 'left',
  background: 'none', border: 'none', cursor: 'pointer',
  padding: '9px 14px', fontSize: 13, color: 'var(--text-primary)',
}

export default function Usuarios() {
  const queryClient = useQueryClient()
  const [menuAbiertoId, setMenuAbiertoId] = useState(null)

  const { data } = useQuery({
    queryKey: ['usuarios'],
    queryFn: () => api.get('/auth/usuarios').then(r => r.data).catch(err => { if (sinBackend(err)) return DEMO; throw err }),
  })

  const usuarios = data || DEMO

  function cerrarMenu() {
    setMenuAbiertoId(null)
  }

  async function activarUsuario(id) {
    cerrarMenu()
    try {
      await api.put(`/auth/usuarios/${id}/activar`)
      toast.success('Usuario activado')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
    } catch {
      toast.error('No se pudo activar el usuario')
    }
  }

  async function desactivarUsuario(id) {
    cerrarMenu()
    try {
      await api.put(`/auth/usuarios/${id}/desactivar`)
      toast.success('Usuario desactivado')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
    } catch {
      toast.error('No se pudo desactivar el usuario')
    }
  }

  async function cambiarPassword(id) {
    cerrarMenu()
    const nueva = window.prompt('Nueva contraseña (mínimo 8 caracteres):')
    if (!nueva) return
    if (nueva.length < 8) return toast.error('La contraseña debe tener al menos 8 caracteres')

    try {
      await api.put(`/auth/usuarios/${id}/cambiar-password`, { password_nueva: nueva })
      toast.success('Contraseña actualizada')
    } catch {
      toast.error('No se pudo cambiar la contraseña')
    }
  }

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
              <MenuUsuario
                usuario={u}
                abierto={menuAbiertoId === u.id}
                onToggle={() => setMenuAbiertoId(menuAbiertoId === u.id ? null : u.id)}
                onActivar={() => activarUsuario(u.id)}
                onDesactivar={() => desactivarUsuario(u.id)}
                onCambiarPassword={() => cambiarPassword(u.id)}
              />
            </motion.div>
          ))
        )}
      </Card>
    </div>
  )
}
