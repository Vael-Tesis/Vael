import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import api from '../../services/api.js'
import Button from '../../components/ui/Button.jsx'

const ETAPAS = {
  CONSENTIMIENTO: 'consentimiento',
  VERIFICACION: 'verificacion',
  SALA: 'sala',
}

export default function EntrevistaVoz() {
  const navigate = useNavigate()
  const [etapa, setEtapa] = useState(ETAPAS.CONSENTIMIENTO)
  const [aceptado, setAceptado] = useState(false)
  const [fotoCapturada, setFotoCapturada] = useState(false)
  const [conectando, setConectando] = useState(false)
  const [hablando, setHablando] = useState(false)
  const [duracion, setDuracion] = useState(0)
  const videoRef = useRef(null)
  const streamRef = useRef(null)

  useEffect(() => {
    if (etapa === ETAPAS.VERIFICACION || etapa === ETAPAS.SALA) {
      navigator.mediaDevices?.getUserMedia({ video: true, audio: etapa === ETAPAS.SALA })
        .then(stream => {
          streamRef.current = stream
          if (videoRef.current) videoRef.current.srcObject = stream
        })
        .catch(() => toast.error('No se pudo acceder a la cámara'))
    }
    return () => streamRef.current?.getTracks().forEach(t => t.stop())
  }, [etapa])

  useEffect(() => {
    if (etapa !== ETAPAS.SALA) return
    const interval = setInterval(() => setDuracion(d => d + 1), 1000)
    return () => clearInterval(interval)
  }, [etapa])

  async function capturarIdentidad() {
  // DEV: saltar validación real si no hay backend
  if (import.meta.env.DEV) {
    setFotoCapturada(true)
    toast.success('Identidad verificada (modo desarrollo)')
    return
  }

  const video = videoRef.current
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  canvas.toBlob(async (blob) => {
    const formData = new FormData()
    formData.append('imagen', blob, 'identidad.jpg')
    formData.append('tipo', 'identidad')
    try {
      await api.post('/entrevista/captura', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setFotoCapturada(true)
      toast.success('Identidad verificada')
    } catch {
      toast.error('No se pudo validar tu rostro, intenta de nuevo')
    }
  }, 'image/jpeg')
}

  async function iniciarEntrevista() {
    setConectando(true)
    
    // DEV: saltar conexión real si no hay backend
    if (import.meta.env.DEV) {
      setTimeout(() => {
        setEtapa(ETAPAS.SALA)
        setConectando(false)
      }, 800)
      return
    }

    try {
      await api.post('/entrevista/iniciar')
      setEtapa(ETAPAS.SALA)
    } catch {
      toast.error('No se pudo iniciar la entrevista')
    } finally {
      setConectando(false)
    }
  }

  async function finalizarEntrevista() {
    try {
      await api.post('/entrevista/finalizar')
    } catch {}
    navigate('/candidato/progreso')
  }

  const min = Math.floor(duracion / 60)
  const seg = duracion % 60

  return (
    <div style={{
      minHeight: 'calc(100vh - 52px)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <AnimatePresence mode="wait">

        {/* Consentimiento */}
        {etapa === ETAPAS.CONSENTIMIENTO && (
          <motion.div key="consentimiento"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{
              width: '100%', maxWidth: 440, background: 'var(--bg-card)',
              border: '1px solid var(--border)', borderRadius: 10, padding: 32,
            }}
          >
            <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
              Entrevista con EVA
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 20 }}>
              Vas a conversar con EVA, nuestra entrevistadora virtual. Para esta etapa necesitamos tu consentimiento para:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
              {[
                'Grabar audio y video durante la entrevista',
                'Tomar capturas periódicas para verificación de identidad',
                'Procesar tus respuestas con inteligencia artificial',
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>·</span> {item}
                </div>
              ))}
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-primary)', cursor: 'pointer', marginBottom: 20 }}>
              <input type="checkbox" checked={aceptado} onChange={e => setAceptado(e.target.checked)} />
              Acepto y doy mi consentimiento
            </label>
            <Button
              disabled={!aceptado}
              onClick={() => setEtapa(ETAPAS.VERIFICACION)}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              Continuar
            </Button>
          </motion.div>
        )}

        {/* Verificación de identidad */}
        {etapa === ETAPAS.VERIFICACION && (
          <motion.div key="verificacion"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{
              width: '100%', maxWidth: 440, background: 'var(--bg-card)',
              border: '1px solid var(--border)', borderRadius: 10, padding: 32, textAlign: 'center',
            }}
          >
            <h1 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>
              Verificación de identidad
            </h1>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              Asegúrate de estar en un lugar bien iluminado y mirar directamente a la cámara
            </p>

            <div style={{
              width: '100%', aspectRatio: '4/3', background: '#000',
              borderRadius: 10, overflow: 'hidden', marginBottom: 20,
              border: fotoCapturada ? '2px solid var(--success-text)' : '1px solid var(--border)',
            }}>
              <video ref={videoRef} autoPlay muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>

            {!fotoCapturada ? (
              <Button onClick={capturarIdentidad} style={{ width: '100%', justifyContent: 'center' }}>
                Tomar foto
              </Button>
            ) : (
              <Button onClick={iniciarEntrevista} disabled={conectando} style={{ width: '100%', justifyContent: 'center' }}>
                {conectando ? 'Conectando con EVA...' : 'Iniciar entrevista'}
              </Button>
            )}
          </motion.div>
        )}

        {/* Sala de entrevista */}
        {etapa === ETAPAS.SALA && (
          <motion.div key="sala"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ width: '100%', maxWidth: 520, textAlign: 'center' }}
          >
            {/* Video oculto, solo para capturas periódicas */}
            <video ref={videoRef} autoPlay muted playsInline style={{ display: 'none' }} />

            <div style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 10, padding: 40,
            }}>
              {/* Indicador de voz animado */}
              <motion.div
                animate={{ scale: hablando ? [1, 1.08, 1] : 1 }}
                transition={{ repeat: hablando ? Infinity : 0, duration: 1.2 }}
                style={{
                  width: 90, height: 90, borderRadius: '50%',
                  background: 'var(--text-primary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 20px', color: 'var(--bg-card)', fontSize: 28, fontWeight: 600,
                }}
              >EVA</motion.div>

              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 4 }}>
                {hablando ? 'EVA está hablando...' : 'Escuchando tu respuesta...'}
              </p>
              <p style={{
                fontSize: 20, fontWeight: 600, color: 'var(--text-primary)',
                fontVariantNumeric: 'tabular-nums', marginBottom: 24,
              }}>
                {String(min).padStart(2, '0')}:{String(seg).padStart(2, '0')}
              </p>

              <Button variant="danger" onClick={finalizarEntrevista}>
                Finalizar entrevista
              </Button>
            </div>

            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 14 }}>
              Tu cámara y micrófono están activos para esta sesión
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}