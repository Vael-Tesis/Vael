import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { irAlLogin, renovarSesion, tokenAcceso } from '../auth/sesion'

/**
 * Cliente axios de las pantallas que aún no migran al cliente tipado (DEC-008).
 * Comparte la sesión y la renovación transparente con src/api/cliente.ts (DEC-011).
 */
const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

const RUTAS_CANDIDATO = [/^\/evaluaciones\/candidato\//, /^\/entrevista\/(acceso|iniciar|finalizar|captura|evento)/]
const RUTAS_DE_SESION = /^\/auth\/(login|refresh|logout)$/

function esRutaCandidato(url: string): boolean {
  return RUTAS_CANDIDATO.some((patron) => patron.test(url))
}

api.interceptors.request.use((config) => {
  const url = config.url ?? ''
  const token = esRutaCandidato(url) ? sessionStorage.getItem('vael_candidate_token') : tokenAcceso()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

type ConfigConReintento = InternalAxiosRequestConfig & { _reintentado?: boolean }

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const config = error.config as ConfigConReintento | undefined
    const url = config?.url ?? ''
    if (error.response?.status !== 401 || !config || esRutaCandidato(url) || RUTAS_DE_SESION.test(url)) {
      return Promise.reject(error)
    }
    if (!config._reintentado) {
      const nuevoToken = await renovarSesion()
      if (nuevoToken) {
        config._reintentado = true
        config.headers.Authorization = `Bearer ${nuevoToken}`
        return api.request(config)
      }
    }
    irAlLogin()
    return Promise.reject(error)
  }
)

export default api
