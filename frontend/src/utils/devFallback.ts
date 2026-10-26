import { isAxiosError } from 'axios'

/** Los datos simulados solo se activan con VITE_MOCKS=true (DEC-008); por defecto están apagados. */
export const MOCKS_ACTIVOS = import.meta.env.VITE_MOCKS === 'true'

// Con los mocks activos, si el backend no responde o devuelve 5xx,
// la UI continúa con datos simulados en lugar de quedarse bloqueada.
export const sinBackend = (err: unknown): boolean => {
  if (!MOCKS_ACTIVOS) return false
  if (!isAxiosError(err)) return false
  return !err.response || err.response.status >= 500
}
