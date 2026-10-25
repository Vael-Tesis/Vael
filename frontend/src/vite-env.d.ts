/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "true" activa los datos simulados de desarrollo (DEC-008). Desactivado por defecto. */
  readonly VITE_MOCKS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
