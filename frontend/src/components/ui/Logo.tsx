/**
 * Logo de VAEL, «el embudo»: dos filtros que se acortan y el elegido (lima), de muchos postulantes
 * a la lista corta. Es el mismo trazo de `public/favicon.svg` y de la landing, con los colores de la
 * paleta (DEC-008) para que siga al tema claro u oscuro.
 */
export default function Logo({ tamano = 28 }: { tamano?: number }) {
  return (
    <svg width={tamano} height={tamano} viewBox="0 0 32 32" role="img" aria-label="VAEL" style={{ flex: 'none', display: 'block' }}>
      <rect width="32" height="32" rx="9" fill="var(--brand)" />
      <path d="M8 9h16" stroke="var(--on-brand)" strokeOpacity=".45" strokeWidth="3" strokeLinecap="round" />
      <path d="M11 14.5h10" stroke="var(--on-brand)" strokeOpacity=".8" strokeWidth="3" strokeLinecap="round" />
      <circle cx="16" cy="21.8" r="3.8" fill="var(--signal)" />
    </svg>
  )
}
