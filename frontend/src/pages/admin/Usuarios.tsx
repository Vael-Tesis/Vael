import { useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, datos, mensajeDe, type Esquemas } from '../../api/cliente'
import { usuarioActual } from '../../auth/sesion'
import Badge, { type BadgeVariant } from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import ConfirmModal from '../../components/ui/ConfirmModal'
import EmptyState from '../../components/ui/EmptyState'
import { Selector, type Opcion } from '../../components/ui/Formulario'
import Input from '../../components/ui/Input'
import PageHeader from '../../components/ui/PageHeader'
import Spinner from '../../components/ui/Spinner'

/**
 * P-19 Usuarios (HU-07, RF-A-18): equipo RRHH con acceso al sistema. Crear, activar,
 * desactivar, cambiar contraseña y reenviar credenciales son solo del admin; listar lo ven
 * admin y gerente (coherente con `auth/permisos.ts`, que ya exige uno de los dos para abrir
 * la ruta). Desactivar o cambiar la contraseña invalidan al instante el token y las sesiones
 * del usuario (`token_version`, DEC-011): la interfaz no necesita hacer nada más para eso, el
 * backend ya lo garantiza (`test_sesiones.py`).
 */

type Usuario = Esquemas['UsuarioResponse']
type Rol = Usuario['rol']

const ROL: Record<Rol, { etiqueta: string; variante: BadgeVariant }> = {
  admin: { etiqueta: 'Admin', variante: 'danger' },
  gerente: { etiqueta: 'Gerente', variante: 'neutral' },
  reclutador: { etiqueta: 'Reclutador', variante: 'info' },
  evaluador: { etiqueta: 'Evaluador', variante: 'warning' },
}

const ROLES: readonly Opcion<Rol>[] = [
  { valor: 'admin', etiqueta: 'Admin' },
  { valor: 'reclutador', etiqueta: 'Reclutador' },
  { valor: 'evaluador', etiqueta: 'Evaluador' },
  { valor: 'gerente', etiqueta: 'Gerente' },
]

function FormularioUsuario({ onCancelar, onCreado }: { onCancelar: () => void; onCreado: () => void }) {
  const [nombre, setNombre] = useState('')
  const [apellidos, setApellidos] = useState('')
  const [email, setEmail] = useState('')
  const [telefono, setTelefono] = useState('')
  const [rol, setRol] = useState<Rol>('reclutador')

  const valido = nombre.trim() !== '' && apellidos.trim() !== '' && email.trim() !== ''

  const crear = useMutation({
    mutationFn: async () =>
      datos(
        await api.POST('/api/auth/usuarios/crear', {
          body: { nombre: nombre.trim(), apellidos: apellidos.trim(), email: email.trim(), rol, telefono: telefono.trim() || null },
        }),
        'No se pudo crear el usuario',
      ),
    onSuccess: () => {
      toast.success('Usuario creado: se le envió la contraseña temporal por correo')
      onCreado()
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo crear el usuario')),
  })

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 16 }}>
      <Card>
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 14 }}>Nuevo usuario</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
          <Input label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <Input label="Apellidos" value={apellidos} onChange={(e) => setApellidos(e.target.value)} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
          <Input label="Correo" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="correo@empresa.com" />
          <Input label="Teléfono (opcional)" value={telefono} onChange={(e) => setTelefono(e.target.value)} />
        </div>
        <div style={{ marginBottom: 14, maxWidth: 220 }}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>Rol</label>
          <Selector valor={rol} onCambio={setRol} opciones={ROLES} />
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
          La contraseña temporal se genera automáticamente y se envía por correo.
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
          <Button variant="secondary" onClick={onCancelar}>Cancelar</Button>
          <Button onClick={() => crear.mutate()} disabled={!valido || crear.isPending}>
            {crear.isPending ? 'Creando...' : 'Crear usuario'}
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

function MenuUsuario({
  usuario, abierto, onToggle, onActivar, onDesactivar, onCambiarPassword, onReenviar,
}: {
  usuario: Usuario
  abierto: boolean
  onToggle: () => void
  onActivar: () => void
  onDesactivar: () => void
  onCambiarPassword: () => void
  onReenviar: () => void
}) {
  return (
    <div style={{ position: 'relative' }}>
      <Button variant="ghost" size="sm" onClick={onToggle}>···</Button>
      {abierto && (
        <>
          <div onClick={onToggle} style={{ position: 'fixed', inset: 0, zIndex: 9 }} />
          <div style={{
            position: 'absolute', right: 0, top: '100%', marginTop: 4, zIndex: 10,
            background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8,
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)', minWidth: 190, overflow: 'hidden',
          }}>
            {usuario.activo ? (
              <button onClick={onDesactivar} style={estiloItemMenu}>Desactivar usuario</button>
            ) : (
              <button onClick={onActivar} style={estiloItemMenu}>Activar usuario</button>
            )}
            <button onClick={onCambiarPassword} style={estiloItemMenu}>Cambiar contraseña</button>
            <button onClick={onReenviar} style={estiloItemMenu}>Reenviar credenciales</button>
          </div>
        </>
      )}
    </div>
  )
}

const estiloItemMenu: CSSProperties = {
  display: 'block', width: '100%', textAlign: 'left',
  background: 'none', border: 'none', cursor: 'pointer',
  padding: '9px 14px', fontSize: 13, color: 'var(--text-primary)',
}

function ModalCambiarPassword({ usuario, onCerrar }: { usuario: Usuario | null; onCerrar: () => void }) {
  const queryClient = useQueryClient()
  const [nueva, setNueva] = useState('')
  const [repetida, setRepetida] = useState('')
  const [intentado, setIntentado] = useState(false)

  const errorNueva = nueva.length < 8 ? 'Mínimo 8 caracteres' : ''
  const errorRepetida = repetida !== nueva ? 'Las contraseñas no coinciden' : ''

  const cambiar = useMutation({
    mutationFn: async () => {
      if (!usuario) return
      return datos(
        await api.PUT('/api/auth/usuarios/{usuario_id}/cambiar-password', {
          params: { path: { usuario_id: usuario.id } },
          body: { password_nueva: nueva },
        }),
        'No se pudo cambiar la contraseña',
      )
    },
    onSuccess: () => {
      toast.success('Contraseña actualizada: la sesión del usuario se cerró al instante')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      onCerrar()
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo cambiar la contraseña')),
  })

  function confirmar() {
    setIntentado(true)
    if (errorNueva || errorRepetida) return
    cambiar.mutate()
  }

  return (
    <ConfirmModal
      abierto={usuario !== null}
      titulo="Cambiar contraseña"
      textoConfirmar="Cambiar contraseña"
      procesando={cambiar.isPending}
      onConfirmar={confirmar}
      onCancelar={onCerrar}
    >
      <p style={{ marginBottom: 14 }}>
        Nueva contraseña para <strong>{usuario?.nombre} {usuario?.apellidos}</strong> ({usuario?.email}).
      </p>
      <form onSubmit={(e) => { e.preventDefault(); confirmar() }} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Input label="Nueva contraseña" type="password" value={nueva} onChange={(e) => setNueva(e.target.value)} error={intentado ? errorNueva : ''} />
        <Input label="Repite la contraseña" type="password" value={repetida} onChange={(e) => setRepetida(e.target.value)} error={intentado ? errorRepetida : ''} />
        <button type="submit" hidden />
      </form>
    </ConfirmModal>
  )
}

export default function Usuarios() {
  const queryClient = useQueryClient()
  const esAdmin = usuarioActual()?.rol === 'admin'
  const [menuAbiertoId, setMenuAbiertoId] = useState<string | null>(null)
  const [creando, setCreando] = useState(false)
  const [cambiandoPassword, setCambiandoPassword] = useState<Usuario | null>(null)

  const usuarios = useQuery({
    queryKey: ['usuarios'],
    queryFn: async () => datos(await api.GET('/api/auth/usuarios'), 'No se pudieron cargar los usuarios'),
  })

  const activar = useMutation({
    mutationFn: async (id: string) => datos(await api.PUT('/api/auth/usuarios/{usuario_id}/activar', { params: { path: { usuario_id: id } } })),
    onSuccess: () => {
      toast.success('Usuario activado')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo activar el usuario')),
  })

  const desactivar = useMutation({
    mutationFn: async (id: string) => datos(await api.PUT('/api/auth/usuarios/{usuario_id}/desactivar', { params: { path: { usuario_id: id } } })),
    onSuccess: () => {
      toast.success('Usuario desactivado: su sesión se cerró al instante')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
    },
    onError: (e) => toast.error(mensajeDe(e, 'No se pudo desactivar el usuario')),
  })

  const reenviar = useMutation({
    mutationFn: async (id: string) => datos(await api.POST('/api/auth/usuarios/{usuario_id}/reenviar-credenciales', { params: { path: { usuario_id: id } } })),
    onSuccess: () => toast.success('Credenciales reenviadas por correo'),
    onError: (e) => toast.error(mensajeDe(e, 'No se pudieron reenviar las credenciales')),
  })

  function cerrarMenu() {
    setMenuAbiertoId(null)
  }

  return (
    <div style={{ padding: '20px 24px' }}>
      <PageHeader
        title="Usuarios"
        description="Equipo RRHH con acceso al sistema"
        action={esAdmin && !creando && <Button onClick={() => setCreando(true)}>+ Nuevo usuario</Button>}
      />

      {creando && (
        <FormularioUsuario
          onCancelar={() => setCreando(false)}
          onCreado={() => { setCreando(false); queryClient.invalidateQueries({ queryKey: ['usuarios'] }) }}
        />
      )}

      <Card padding="0">
        <div style={{
          display: 'grid', gridTemplateColumns: esAdmin ? '1fr 180px 100px 80px 40px' : '1fr 180px 100px 80px',
          padding: '8px 16px', borderBottom: '1px solid var(--border)',
          fontSize: 11, fontWeight: 500, color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.05em', gap: 12,
        }}>
          <span>Usuario</span>
          <span>Correo</span>
          <span>Rol</span>
          <span>Estado</span>
          {esAdmin && <span />}
        </div>

        {usuarios.isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}><Spinner /></div>
        ) : usuarios.error ? (
          <EmptyState title="No se pudieron cargar los usuarios" description={mensajeDe(usuarios.error, 'Intenta de nuevo')} />
        ) : (usuarios.data ?? []).length === 0 ? (
          <EmptyState title="Sin usuarios" />
        ) : (
          (usuarios.data ?? []).map((u, i) => (
            <motion.div key={u.id}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
              style={{
                display: 'grid', gridTemplateColumns: esAdmin ? '1fr 180px 100px 80px 40px' : '1fr 180px 100px 80px',
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
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{u.nombre} {u.apellidos}</p>
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.email}</span>
              <Badge variant={ROL[u.rol].variante}>{ROL[u.rol].etiqueta}</Badge>
              <Badge variant={u.activo ? 'success' : 'neutral'}>{u.activo ? 'Activo' : 'Inactivo'}</Badge>
              {esAdmin && (
                <MenuUsuario
                  usuario={u}
                  abierto={menuAbiertoId === u.id}
                  onToggle={() => setMenuAbiertoId(menuAbiertoId === u.id ? null : u.id)}
                  onActivar={() => { cerrarMenu(); activar.mutate(u.id) }}
                  onDesactivar={() => { cerrarMenu(); desactivar.mutate(u.id) }}
                  onCambiarPassword={() => { cerrarMenu(); setCambiandoPassword(u) }}
                  onReenviar={() => { cerrarMenu(); reenviar.mutate(u.id) }}
                />
              )}
            </motion.div>
          ))
        )}
      </Card>

      {/* key: cada apertura empieza con los campos vacíos */}
      <ModalCambiarPassword key={cambiandoPassword?.id ?? 'cerrado'} usuario={cambiandoPassword} onCerrar={() => setCambiandoPassword(null)} />
    </div>
  )
}
