import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../services/api.js'

export default function Login() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
  e.preventDefault()
  setLoading(true)

  try {
    const { data } = await api.post('/auth/login', form)
    localStorage.setItem('vael_token', data.access_token)

    const { data: usuario } = await api.get('/auth/perfil')
    localStorage.setItem('vael_user', JSON.stringify(usuario))
    toast.success(`Bienvenido, ${usuario.nombre}`)
    navigate('/dashboard')
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Credenciales incorrectas')
  } finally {
    setLoading(false)
  }
}

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-page)',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
        style={{
          width: '100%', maxWidth: 360,
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 10,
          padding: 32,
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 36, height: 36,
            background: 'var(--text-primary)',
            borderRadius: 8,
            display: 'inline-flex',
            alignItems: 'center', justifyContent: 'center',
            color: 'var(--bg-card)',
            fontSize: 13, fontWeight: 600,
            marginBottom: 12,
          }}>VA</div>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
            Bienvenido a VAEL
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
            Panel de administración RRHH
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <label style={{
              display: 'block', fontSize: 12, fontWeight: 500,
              color: 'var(--text-secondary)', marginBottom: 5,
            }}>
              Correo electrónico
            </label>
            <input
              type="email"
              required
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="tu@empresa.com"
              style={{
                width: '100%', height: 36,
                padding: '0 12px',
                border: '1px solid var(--border)',
                borderRadius: 6,
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                fontSize: 13,
                outline: 'none',
                transition: 'border-color 150ms ease',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--text-primary)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{
              display: 'block', fontSize: 12, fontWeight: 500,
              color: 'var(--text-secondary)', marginBottom: 5,
            }}>
              Contraseña
            </label>
            <input
              type="password"
              required
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="••••••••"
              style={{
                width: '100%', height: 36,
                padding: '0 12px',
                border: '1px solid var(--border)',
                borderRadius: 6,
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                fontSize: 13,
                outline: 'none',
                transition: 'border-color 150ms ease',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--text-primary)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'}
            />
          </div>

          <motion.button
            type="submit"
            disabled={loading}
            whileTap={{ scale: 0.98 }}
            style={{
              width: '100%', height: 36,
              background: 'var(--text-primary)',
              color: 'var(--bg-card)',
              border: 'none', borderRadius: 6,
              fontSize: 13, fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
              transition: 'opacity 150ms ease',
            }}
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </motion.button>
        </form>
      </motion.div>
    </div>
  )
}