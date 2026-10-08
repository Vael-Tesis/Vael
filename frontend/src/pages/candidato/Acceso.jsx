import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import Button from '../../components/ui/Button.jsx'
import Input from '../../components/ui/Input.jsx'

export default function Acceso() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [codigo, setCodigo] = useState('')
  const [loading, setLoading] = useState(false)

  // Precarga el token si viene desde el link del correo
  useEffect(() => {
    const token = searchParams.get('token')
    if (token) {
      accederConToken(token)
    }
  }, [])

  function decodificarTipo(token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.tipo
    } catch {
      return null
    }
  }

  async function accederConToken(token) {
    setLoading(true)
    sessionStorage.setItem('vael_candidate_token', token)

    const tipo = decodificarTipo(token)
    const ruta = tipo === 'entrevista' ? '/entrevista/acceso' : '/evaluaciones/candidato/acceso'

    try {
      const { data } = await api.post(ruta)
      sessionStorage.setItem('vael_candidate_data', JSON.stringify(data))
      navigate('/candidato/instrucciones')
    } catch (err) {
      sessionStorage.removeItem('vael_candidate_token')
      toast.error(err.response?.data?.detail || 'Código inválido o expirado')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!codigo.trim()) return
    setLoading(true)
    try {
      const { data } = await api.post('/evaluaciones/candidato/resolver-codigo', {
        codigo_corto: codigo.trim().toUpperCase(),
      })
      await accederConToken(data.token)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Código inválido o expirado')
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: 'calc(100vh - 52px)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        style={{
          width: '100%', maxWidth: 380, background: 'var(--bg-card)',
          border: '1px solid var(--border)', borderRadius: 10, padding: 32,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
            Accede a tu proceso
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
            Ingresa el código que recibiste por correo
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <Input
              label="Código de acceso"
              value={codigo}
              onChange={e => setCodigo(e.target.value)}
              placeholder="VAEL-XXXX-XXXX"
            />
          </div>
          <Button type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
            {loading ? 'Verificando...' : 'Ingresar'}
          </Button>
        </form>

        <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', marginTop: 16 }}>
          ¿No tienes el código? Revisa el correo que te enviamos al postular.
        </p>
      </motion.div>
    </div>
  )
}