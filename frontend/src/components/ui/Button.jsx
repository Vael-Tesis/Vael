import { motion } from 'framer-motion'

export default function Button({
  children, onClick, type = 'button',
  variant = 'primary', size = 'md',
  disabled = false, style = {},
}) {
  const sizes = { sm: '6px 12px', md: '7px 16px', lg: '9px 20px' }
  const base = {
    border: 'none', borderRadius: 6, cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: 500, display: 'inline-flex', alignItems: 'center',
    gap: 6, whiteSpace: 'nowrap', transition: 'opacity 150ms ease',
    opacity: disabled ? 0.5 : 1,
    fontSize: size === 'sm' ? 12 : size === 'lg' ? 14 : 13,
    padding: sizes[size] || sizes.md,
  }
  const variants = {
    primary:  { background: 'var(--text-primary)', color: 'var(--bg-card)' },
    secondary:{ background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border)' },
    ghost:    { background: 'transparent', color: 'var(--text-secondary)' },
    danger:   { background: 'var(--danger-bg)', color: 'var(--danger-text)' },
  }
  return (
    <motion.button
      type={type} onClick={onClick} disabled={disabled}
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      style={{ ...base, ...variants[variant], ...style }}
    >
      {children}
    </motion.button>
  )
}