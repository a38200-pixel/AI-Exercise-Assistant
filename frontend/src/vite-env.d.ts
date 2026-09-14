/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DESKTOP_CLIENT_DOWNLOAD_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
