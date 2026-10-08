export default function Card({ children, style = {}, padding = '16px' }) {
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