import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import Button from '../../components/ui/Button.jsx'
import Card from '../../components/ui/Card.jsx'

const candidatoData = JSON.parse(sessionStorage.getItem('vael_candidate_data') || '{}')

const REGLAS = [
  'Tendrás 45 minutos para completar el examen desde que lo inicies',
  'El examen consta de 10 preguntas: 6 de opción múltiple y 4 abiertas',
  'Tus respuestas se guardan automáticamente mientras avanzas',
  'Si pierdes la conexión, puedes retomar el examen desde donde lo dejaste',
  'Evita cambiar de pestaña o salir de la ventana del examen',
  'No está permitido copiar y pegar texto durante la evaluación',
  'Asegúrate de tener una conexión estable antes de comenzar',
]

export default function ExamenInstrucciones() {
  const candidatoData = JSON.parse(sessionStorage.getItem('vael_candidate_data') || '{}')
  const navigate = useNavigate()

  return (
    <div style={{
      minHeight: 'calc(100vh - 52px)', display: 'flex',
      justifyContent: 'center', padding: '40px 20px',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        style={{ width: '100%', maxWidth: 560 }}
      >
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
            Antes de comenzar
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
            Examen técnico · {candidatoData.vacante?.titulo || 'Evaluación'}
          </p>
        </div>

        <Card style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Instrucciones
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {REGLAS.map((regla, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{
                  width: 18, height: 18, borderRadius: '50%',
                  background: 'var(--bg-page)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 600, color: 'var(--text-secondary)',
                  flexShrink: 0, marginTop: 1,
                }}>{i + 1}</span>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{regla}</p>
              </div>
            ))}
          </div>
        </Card>

        <Button onClick={() => navigate('/candidato/examen')} style={{ width: '100%', justifyContent: 'center' }}>
          Comenzar examen
        </Button>
      </motion.div>
    </div>
  )
}