/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_GITHUB_URL?: string
  readonly VITE_COMMIT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
