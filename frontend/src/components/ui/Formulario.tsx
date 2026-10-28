import type { ChangeEventHandler, CSSProperties, ReactNode } from 'react'

/** Piezas de formulario compartidas por las pantallas migradas (DEC-008). */

export const estiloControl: CSSProperties = {
  width: '100%',
  height: 36,
  padding: '0 12px',
  border: '1px solid var(--border)',
  borderRadius: 6,
  background: 'var(--bg-card)',
  color: 'var(--text-primary)',
  fontSize: 13,
  outline: 'none',
}

export function Campo({ etiqueta, htmlFor, children, ayuda }: { etiqueta: string; htmlFor?: string; children: ReactNode; ayuda?: ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label htmlFor={htmlFor} style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 5 }}>
        {etiqueta}
      </label>
      {children}
      {ayuda && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>{ayuda}</p>}
    </div>
  )
}

export interface Opcion<T extends string> {
  valor: T
  etiqueta: string
}

export function Selector<T extends string>({
  id, valor, opciones, onCambio, deshabilitado = false,
}: {
  id?: string
  valor: T
  opciones: readonly Opcion<T>[]
  onCambio: (valor: T) => void
  deshabilitado?: boolean
}) {
  return (
    <select
      id={id}
      value={valor}
      disabled={deshabilitado}
      onChange={(e) => onCambio(e.target.value as T)}
      style={{ ...estiloControl, cursor: deshabilitado ? 'not-allowed' : 'pointer', opacity: deshabilitado ? 0.6 : 1 }}
    >
      {opciones.map((o) => <option key={o.valor} value={o.valor}>{o.etiqueta}</option>)}
    </select>
  )
}

export function AreaTexto({
  id, valor, onChange, placeholder, filas = 3,
}: {
  id?: string
  valor: string
  onChange: ChangeEventHandler<HTMLTextAreaElement>
  placeholder?: string
  filas?: number
}) {
  return (
    <textarea
      id={id}
      value={valor}
      onChange={onChange}
      placeholder={placeholder}
      rows={filas}
      style={{ ...estiloControl, height: 'auto', padding: 10, fontFamily: 'inherit', resize: 'vertical' }}
    />
  )
}

export function Pestanas<T extends string>({ actual, opciones, onCambio }: { actual: T; opciones: readonly Opcion<T>[]; onCambio: (valor: T) => void }) {
  return (
    <div role="tablist" style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 16, overflowX: 'auto' }}>
      {opciones.map((o) => (
        <button
          key={o.valor}
          role="tab"
          aria-selected={actual === o.valor}
          onClick={() => onCambio(o.valor)}
          style={{
            background: 'none', border: 'none', cursor: 'pointer', padding: '8px 14px', fontSize: 13, fontWeight: 500,
            whiteSpace: 'nowrap',
            color: actual === o.valor ? 'var(--brand)' : 'var(--text-muted)',
            borderBottom: actual === o.valor ? '2px solid var(--brand)' : '2px solid transparent',
            marginBottom: -1,
          }}
        >
          {o.etiqueta}
        </button>
      ))}
    </div>
  )
}

export function Filtros<T extends string>({ actual, opciones, onCambio }: { actual: T; opciones: readonly Opcion<T>[]; onCambio: (valor: T) => void }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
      {opciones.map((o) => (
        <button
          key={o.valor}
          onClick={() => onCambio(o.valor)}
          aria-pressed={actual === o.valor}
          style={{
            padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border)', transition: 'all 150ms ease',
            background: actual === o.valor ? 'var(--brand)' : 'var(--bg-card)',
            color: actual === o.valor ? 'var(--on-brand)' : 'var(--text-secondary)',
          }}
        >
          {o.etiqueta}
        </button>
      ))}
    </div>
  )
}

export function Volver({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button onClick={onClick} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 12, marginBottom: 14, padding: 0 }}>
      ← {children}
    </button>
  )
}
