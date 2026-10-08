import { useState } from 'react'

export default function Input({
  label, type = 'text', value, onChange,
  placeholder, required, error,
}) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {label && (
        <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>
          {label}
        </label>
      )}
      <input
        type={type} value={value} onChange={onChange}
        placeholder={placeholder} required={required}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          height: 36, padding: '0 12px',
          border: `1px solid ${error ? 'var(--danger-text)' : focused ? 'var(--text-primary)' : 'var(--border)'}`,
          borderRadius: 6,
          background: 'var(--bg-card)',
          color: 'var(--text-primary)',
          fontSize: 13, outline: 'none',
          transition: 'border-color 150ms ease',
          width: '100%',
        }}
      />
      {error && <p style={{ fontSize: 11, color: 'var(--danger-text)' }}>{error}</p>}
    </div>
  )
}