export default function EmptyState({ title = 'Sin resultados', description = '' }) {
  return (
    <div style={{
      padding: '48px 24px', textAlign: 'center',
      color: 'var(--text-muted)',
    }}>
      <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>
        {title}
      </p>
      {description && <p style={{ fontSize: 13 }}>{description}</p>}
    </div>
  )
}