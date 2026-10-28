/**
 * Verificación del contrato tipado (DEC-008, DEV-C-09). Este archivo no se ejecuta: lo
 * revisa `tsc --noEmit` en el CI. Cada `@ts-expect-error` exige que la línea siguiente NO
 * compile; si el backend llegara a aceptar esa ruta o ese campo, la directiva sobraría y el
 * CI fallaría. Así queda probado que una ruta o un campo inexistente rompe la compilación.
 */
import { api } from './cliente'

export async function verificarContrato(): Promise<void> {
  // Las dos llamadas desalineadas que detectó DEC-008:
  // @ts-expect-error la ruta real es GET /api/entrevista
  await api.GET('/api/entrevista/lista')
  // @ts-expect-error la ruta real es GET /api/plantillas
  await api.GET('/api/entrevista/plantillas')

  await api.POST('/api/candidatos/{candidato_id}/decision', {
    params: { path: { candidato_id: 'id' } },
    body: {
      etapa: 'cv',
      decision: 'avanzar',
      // @ts-expect-error campo que no existe en DecisionRequest
      campo_inexistente: true,
    },
  })

  await api.POST('/api/candidatos/{candidato_id}/decision', {
    params: { path: { candidato_id: 'id' } },
    // @ts-expect-error valor fuera del enum de la etapa
    body: { etapa: 'otra', decision: 'avanzar' },
  })

  // Las rutas reales sí compilan
  await api.GET('/api/entrevista')
  await api.GET('/api/plantillas')
}
