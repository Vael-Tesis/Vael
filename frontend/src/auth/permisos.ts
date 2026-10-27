import type { Rol } from './sesion'

/**
 * Pantallas del panel por rol (HU-03, doc 05): admin todo; gerente lectura de todo y
 * decisiones; reclutador vacantes y candidatos; evaluador solo evaluaciones.
 * Es la capa de interfaz: el backend vuelve a verificar cada permiso (403).
 */

const TODOS: readonly Rol[] = ['admin', 'gerente', 'reclutador', 'evaluador']
const GESTION: readonly Rol[] = ['admin', 'gerente', 'reclutador']
const CONFIGURACION: readonly Rol[] = ['admin', 'gerente']

const PERMISOS: ReadonlyArray<[prefijo: string, roles: readonly Rol[]]> = [
  ['/dashboard', TODOS],
  ['/vacantes', GESTION],
  ['/candidatos', GESTION],
  ['/bandeja', GESTION],
  ['/ranking', GESTION],
  ['/banco-talento', GESTION],
  ['/examenes', TODOS],
  ['/entrevistas', TODOS],
  ['/auditoria', TODOS],
  ['/plantillas', CONFIGURACION],
  ['/areas', CONFIGURACION],
  ['/usuarios', CONFIGURACION],
]

/** Si el rol puede abrir la ruta. Una ruta sin regla solo la abre el admin. */
export function puedeVer(rol: Rol | undefined, ruta: string): boolean {
  if (!rol) return false
  const regla = PERMISOS.find(([prefijo]) => ruta === prefijo || ruta.startsWith(`${prefijo}/`))
  return regla ? regla[1].includes(rol) : rol === 'admin'
}

/** Roles que pueden confirmar o revertir recomendaciones de la IA (DEC-009, punto 6). */
export function puedeDecidir(rol: Rol | undefined): boolean {
  return rol !== undefined && GESTION.includes(rol)
}
