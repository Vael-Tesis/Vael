import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import Button from '../../components/ui/Button.jsx'

export default function SesionExpirada() {
  const navigate = useNavigate()
  return (
    <div style={{
      minHeight: 'calc(100vh - 52px)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        style={{
          width: '100%', maxWidth: 400, textAlign: 'center',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 32,
        }}
      >
        <div style={{
          width: 44, height: 44, borderRadius: '50%',
          background: 'var(--warning-bg)', color: 'var(--warning-text)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, margin: '0 auto 14px',
        }}>!</div>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
          Tu sesión expiró
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20, lineHeight: 1.5 }}>
          El link de acceso venció. Revisa tu correo para obtener un nuevo enlace o contacta al equipo de RRHH.
        </p>
        <Button onClick={() => navigate('/candidato/acceso')} style={{ width: '100%', justifyContent: 'center' }}>
          Volver a intentar
        </Button>
      </motion.div>
    </div>
  )
}