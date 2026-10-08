// Solo en desarrollo: si el backend no responde o devuelve 5xx,
// la UI continúa con datos simulados en lugar de quedarse bloqueada.
export const sinBackend = (err) =>
  import.meta.env.DEV && (!err.response || err.response.status >= 500)