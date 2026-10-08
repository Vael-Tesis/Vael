import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import Button from '../../components/ui/Button.jsx'

export default function ExamenFinalizado() {
  const navigate = useNavigate()

  return (
    <div style={{
      minHeight: 'calc(100vh - 52px)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        style={{
          width: '100%', maxWidth: 420, textAlign: 'center',
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 36,
        }}
      >
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: 'var(--success-bg)', color: 'var(--success-text)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, margin: '0 auto 16px',
        }}>✓</div>

        <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
          Examen enviado
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: 24 }}>
          Tus respuestas fueron registradas correctamente. Te notificaremos por correo sobre los siguientes pasos de tu proceso.
        </p>

        <Button onClick={() => navigate('/candidato/progreso')} style={{ width: '100%', justifyContent: 'center' }}>
          Ver mi progreso
        </Button>
      </motion.div>
    </div>
  )
}