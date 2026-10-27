import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './esquema'

/**
 * Cliente HTTP tipado, generado desde el OpenAPI del backend (DEC-008).
 * Las rutas, los parámetros y los cuerpos se verifican al compilar: una ruta o un campo
 * que no existe en el backend no compila. Regenerar con `npm run api:generar`.
 */

export type Esquemas = components['schemas']

export const CLAVE_TOKEN_USUARIO = 'vael_token'
export const CLAVE_USUARIO = 'vael_user'
export const CLAVE_TOKEN_CANDIDATO = 'vael_candidate_token'

const RUTAS_CANDIDATO = [/^\/api\/evaluaciones\/candidato\//, /^\/api\/entrevista\/(acceso|iniciar|finalizar|captura|evento)/]

function tokenPara(ruta: string): string | null {
  const esRutaCandidato = RUTAS_CANDIDATO.some((patron) => patron.test(ruta))
  return esRutaCandidato ? sessionStorage.getItem(CLAVE_TOKEN_CANDIDATO) : localStorage.getItem(CLAVE_TOKEN_USUARIO)
}

const autenticacion: Middleware = {
  onRequest({ request }) {
    const token = tokenPara(new URL(request.url).pathname)
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401 && !tokenPara('/api/evaluaciones/candidato/')) {
      localStorage.removeItem(CLAVE_TOKEN_USUARIO)
      localStorage.removeItem(CLAVE_USUARIO)
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }
    return response
  },
}

export const api = createClient<paths>({ baseUrl: window.location.origin })
api.use(autenticacion)

/** Mensaje legible del `detail` de un error de FastAPI (texto o lista de validaciones). */
export function mensajeDeError(error: unknown, porDefecto: string): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const { detail } = error as { detail: unknown }
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const primero = detail[0] as { msg?: unknown }
      if (typeof primero.msg === 'string') return primero.msg
    }
  }
  return porDefecto
}
