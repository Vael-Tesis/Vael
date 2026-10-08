export default function PageHeader({ title, description, action }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start',
      justifyContent: 'space-between', marginBottom: 20,
    }}>
      <div>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h1>
        {description && (
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>{description}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}