import axios, { type AxiosError } from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

const RUTAS_CANDIDATO = [/^\/evaluaciones\/candidato\//, /^\/entrevista\/(acceso|iniciar|finalizar|captura|evento)/]

api.interceptors.request.use((config) => {
  const url = config.url ?? ''
  const esRutaCandidato = RUTAS_CANDIDATO.some((patron) => patron.test(url))
  const token = esRutaCandidato
    ? sessionStorage.getItem('vael_candidate_token')
    : localStorage.getItem('vael_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('vael_token')
      localStorage.removeItem('vael_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
