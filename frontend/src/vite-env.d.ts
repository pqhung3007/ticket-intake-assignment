/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEV_AUTH?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
