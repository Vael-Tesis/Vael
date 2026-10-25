import type { Esquemas } from '../api/cliente'

/**
 * Sesión del usuario de RRHH en el navegador (DEC-011, HU-01 y HU-02).
 * El access token dura 15 minutos; cuando una petición recibe 401, `renovarSesion` usa el
 * refresh token para obtener un par nuevo (el refresh rota en cada uso) y la petición se
 * reintenta una vez. Si la renovación falla, la sesión se cierra y se vuelve al login.
 */

export type Usuario = Esquemas['UsuarioResponse']
export type Rol = Usuario['rol']

const CLAVE_ACCESS = 'vael_token'
const CLAVE_REFRESH = 'vael_refresh_token'
const CLAVE_USUARIO = 'vael_user'

export function tokenAcceso(): string | null {
  return localStorage.getItem(CLAVE_ACCESS)
}

export function usuarioActual(): Usuario | null {
  try {
    const guardado = localStorage.getItem(CLAVE_USUARIO)
    return guardado ? (JSON.parse(guardado) as Usuario) : null
  } catch {
    return null
  }
}

export function guardarTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(CLAVE_ACCESS, accessToken)
  localStorage.setItem(CLAVE_REFRESH, refreshToken)
}

export function guardarUsuario(usuario: Usuario): void {
  localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario))
}

export function limpiarSesion(): void {
  localStorage.removeItem(CLAVE_ACCESS)
  localStorage.removeItem(CLAVE_REFRESH)
  localStorage.removeItem(CLAVE_USUARIO)
}

export function irAlLogin(): void {
  limpiarSesion()
  if (window.location.pathname !== '/login') window.location.assign('/login')
}

// Una sola renovación a la vez: si varias peticiones reciben 401 juntas, todas esperan la
// misma. Dos renovaciones en paralelo con el mismo refresh token se verían como reutilización
// y el backend cerraría todas las sesiones (DEC-011).
let renovacionEnCurso: Promise<string | null> | null = null

async function pedirRenovacion(): Promise<string | null> {
  const refreshToken = localStorage.getItem(CLAVE_REFRESH)
  if (!refreshToken) return null
  try {
    const respuesta = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!respuesta.ok) return null
    const tokens = (await respuesta.json()) as Esquemas['TokenResponse']
    guardarTokens(tokens.access_token, tokens.refresh_token)
    return tokens.access_token
  } catch {
    return null
  }
}

/** Renueva el access token; retorna el nuevo o null si la sesión ya no es válida. */
export function renovarSesion(): Promise<string | null> {
  renovacionEnCurso ??= pedirRenovacion().finally(() => {
    renovacionEnCurso = null
  })
  return renovacionEnCurso
}

/** Logout efectivo: revoca el refresh token en el backend y limpia el navegador. */
export async function cerrarSesion(): Promise<void> {
  const accessToken = tokenAcceso()
  const refreshToken = localStorage.getItem(CLAVE_REFRESH)
  if (accessToken && refreshToken) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
    } catch {
      // Sin conexión: igual se limpia la sesión local; el refresh expira solo.
    }
  }
  limpiarSesion()
}
