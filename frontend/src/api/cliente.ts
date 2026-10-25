import createClient, { type Middleware } from 'openapi-fetch'
import { irAlLogin, renovarSesion, tokenAcceso } from '../auth/sesion'
import type { components, paths } from './esquema'

/**
 * Cliente HTTP tipado, generado desde el OpenAPI del backend (DEC-008).
 * Las rutas, los parámetros y los cuerpos se verifican al compilar: una ruta o un campo
 * que no existe en el backend no compila. Regenerar con `npm run api:generar`.
 */

export type Esquemas = components['schemas']

export const CLAVE_TOKEN_CANDIDATO = 'vael_candidate_token'

const RUTAS_CANDIDATO = [/^\/api\/evaluaciones\/candidato\//, /^\/api\/entrevista\/(acceso|iniciar|finalizar|captura|evento)/]
const RUTAS_DE_SESION = /^\/api\/auth\/(login|refresh|logout)$/

function esRutaCandidato(ruta: string): boolean {
  return RUTAS_CANDIDATO.some((patron) => patron.test(ruta))
}

function tokenPara(ruta: string): string | null {
  return esRutaCandidato(ruta) ? sessionStorage.getItem(CLAVE_TOKEN_CANDIDATO) : tokenAcceso()
}

// Copia de cada petición antes de enviarla: si responde 401, se reintenta con el token renovado.
const pendientes = new Map<string, Request>()

const autenticacion: Middleware = {
  onRequest({ request, id }) {
    const token = tokenPara(new URL(request.url).pathname)
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    pendientes.set(id, request.clone())
    return request
  },
  async onResponse({ response, id }) {
    const original = pendientes.get(id)
    pendientes.delete(id)
    const ruta = original ? new URL(original.url).pathname : ''
    if (response.status !== 401 || !original || esRutaCandidato(ruta) || RUTAS_DE_SESION.test(ruta)) {
      return response
    }
    // Renovación transparente (DEC-011): un intento con el refresh token y se reintenta.
    const nuevoToken = await renovarSesion()
    if (!nuevoToken) {
      irAlLogin()
      return response
    }
    const reintento = new Request(original, { headers: new Headers(original.headers) })
    reintento.headers.set('Authorization', `Bearer ${nuevoToken}`)
    return fetch(reintento)
  },
  onError({ id }) {
    pendientes.delete(id)
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

/** Error de una llamada a la API, con el estado HTTP y el mensaje del backend. */
export class ErrorApi extends Error {
  readonly estado: number

  constructor(estado: number, mensaje: string) {
    super(mensaje)
    this.estado = estado
  }
}

interface ResultadoApi<T> {
  data?: T
  error?: unknown
  response: Response
}

/** Datos de una respuesta del cliente tipado; si la API respondió con error, lo lanza como ErrorApi. */
export function datos<T>(resultado: ResultadoApi<T>, porDefecto = 'No se pudo completar la operación'): T {
  if (resultado.data === undefined) {
    throw new ErrorApi(resultado.response.status, mensajeDeError(resultado.error, porDefecto))
  }
  return resultado.data
}

/** Mensaje de un error capturado (ErrorApi, error de red u otro). */
export function mensajeDe(error: unknown, porDefecto: string): string {
  if (error instanceof ErrorApi) return error.message
  return porDefecto
}
