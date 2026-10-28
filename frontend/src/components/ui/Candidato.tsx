import Badge from './Badge'

/** Piezas visuales de un candidato, compartidas por el listado, el detalle y la bandeja. */

export function PuntajeCv({ valor }: { valor: number | null }) {
  if (valor === null) return <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>—</span>
  const variante = valor >= 80 ? 'success' : valor >= 60 ? 'warning' : 'danger'
  return <Badge variant={variante}>{valor}</Badge>
}

export function Iniciales({ nombre, apellidos, tamano = 32 }: { nombre: string; apellidos: string; tamano?: number }) {
  return (
    <div aria-hidden style={{
      width: tamano, height: tamano, borderRadius: '50%', background: 'var(--brand-soft)', color: 'var(--brand)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: Math.round(tamano / 3), fontWeight: 600, flexShrink: 0,
    }}>
      {(nombre[0] ?? '') + (apellidos[0] ?? '')}
    </div>
  )
}
