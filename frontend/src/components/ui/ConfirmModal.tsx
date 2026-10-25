import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Button from './Button'

interface ConfirmModalProps {
  abierto: boolean
  titulo: string
  children?: ReactNode
  textoConfirmar?: string
  peligroso?: boolean
  procesando?: boolean
  onConfirmar: () => void
  onCancelar: () => void
}

/** Confirmación antes de una acción irreversible (doc 15, elemento transversal). */
export default function ConfirmModal({
  abierto, titulo, children, textoConfirmar = 'Confirmar', peligroso = false, procesando = false,
  onConfirmar, onCancelar,
}: ConfirmModalProps) {
  return (
    <AnimatePresence>
      {abierto && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onCancelar}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(16, 32, 27, 0.45)', zIndex: 50,
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
          }}
        >
          <motion.div
            role="dialog" aria-modal="true" aria-label={titulo}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%', maxWidth: 420, background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 10, padding: 20,
            }}
          >
            <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>{titulo}</p>
            {children && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>{children}</div>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button variant="secondary" onClick={onCancelar} disabled={procesando}>Cancelar</Button>
              <Button variant={peligroso ? 'danger' : 'primary'} onClick={onConfirmar} disabled={procesando}>
                {procesando ? 'Procesando...' : textoConfirmar}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
