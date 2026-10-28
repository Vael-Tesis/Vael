import type { ReactNode } from 'react'

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

const VARIANTS: Record<BadgeVariant, { bg: string; color: string }> = {
  success: { bg: 'var(--success-bg)', color: 'var(--success-text)' },
  warning: { bg: 'var(--warning-bg)', color: 'var(--warning-text)' },
  danger:  { bg: 'var(--danger-bg)',  color: 'var(--danger-text)'  },
  info:    { bg: 'var(--info-bg)',    color: 'var(--info-text)'    },
  neutral: { bg: 'var(--bg-page)',    color: 'var(--text-secondary)' },
}

interface BadgeProps {
  variant?: BadgeVariant
  children?: ReactNode
}

export default function Badge({ variant = 'neutral', children }: BadgeProps) {
  const s = VARIANTS[variant] || VARIANTS.neutral
  return (
    <span style={{
      background: s.bg, color: s.color,
      fontSize: 11, fontWeight: 500,
      borderRadius: 4, padding: '2px 7px',
      whiteSpace: 'nowrap', display: 'inline-block',
    }}>
      {children}
    </span>
  )
}