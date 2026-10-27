import type { CSSProperties, ReactNode } from 'react'

interface CardProps {
  children?: ReactNode
  style?: CSSProperties
  padding?: CSSProperties['padding']
}

export default function Card({ children, style = {}, padding = '16px' }: CardProps) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding,
      ...style,
    }}>
      {children}
    </div>
  )
}