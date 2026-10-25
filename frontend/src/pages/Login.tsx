import { useState, type CSSProperties, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { api, mensajeDeError } from '../api/cliente'
import { guardarTokens, guardarUsuario, limpiarSesion, tokenAcceso } from '../auth/sesion'

/** P-01 Login (HU-01, RF-A-01): 401 con credenciales inválidas, 403 si el usuario está inactivo. */

const estiloInput: CSSProperties = {
  width: '100%',
  height: 36,
  padding: '0 12px',
  border: '1px solid var(--border)',
  borderRadius: 6,
  background: 'var(--bg-card)',
  color: 'var(--text-primary)',
  fontSize: 13,
  outline: 'none',
  transition: 'border-color 150ms ease',
}

const estiloEtiqueta: CSSProperties = {
  display: 'block',
  fontSize: 12,
  fontWeight: 500,
  color: 'var(--text-secondary)',
  marginBottom: 5,
}

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (tokenAcceso()) return <Navigate to="/dashboard" replace />

  async function ingresar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setEnviando(true)
    try {
      const login = await api.POST('/api/auth/login', { body: { email, password } })
      if (!login.data) {
        const porDefecto = login.response.status === 403 ? 'Tu usuario está inactivo' : 'Correo o contraseña incorrectos'
        toast.error(mensajeDeError(login.error, porDefecto))
        return
      }
      guardarTokens(login.data.access_token, login.data.refresh_token)

      const perfil = await api.GET('/api/auth/perfil')
      if (!perfil.data) {
        limpiarSesion()
        toast.error('No se pudo cargar tu perfil')
        return
      }
      guardarUsuario(perfil.data)
      toast.success(`Bienvenido, ${perfil.data.nombre}`)
      navigate('/dashboard', { replace: true })
    } catch {
      toast.error('No se pudo conectar con el servidor')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-page)', padding: 16 }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
        style={{ width: '100%', maxWidth: 360, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 32 }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 36, height: 36, background: 'var(--brand)', borderRadius: 8,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--on-brand)', fontSize: 13, fontWeight: 600, marginBottom: 12,
          }}>VA</div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>Bienvenido a VAEL</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>Panel de Recursos Humanos</p>
        </div>

        <form onSubmit={ingresar}>
          <div style={{ marginBottom: 14 }}>
            <label htmlFor="email" style={estiloEtiqueta}>Correo electrónico</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@empresa.com"
              style={estiloInput}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label htmlFor="password" style={estiloEtiqueta}>Contraseña</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={estiloInput}
            />
          </div>

          <motion.button
            type="submit"
            disabled={enviando}
            whileTap={{ scale: 0.98 }}
            style={{
              width: '100%', height: 36, background: 'var(--brand)', color: 'var(--on-brand)',
              border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 500,
              cursor: enviando ? 'not-allowed' : 'pointer', opacity: enviando ? 0.6 : 1,
              transition: 'opacity 150ms ease',
            }}
          >
            {enviando ? 'Ingresando...' : 'Ingresar'}
          </motion.button>
        </form>
      </motion.div>
    </div>
  )
}
