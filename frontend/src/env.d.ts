/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_REQUEST_TIMEOUT_MS?: string
  readonly VITE_POLL_INTERVAL_MS?: string
  readonly VITE_MAX_IMAGE_SIZE_MB?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
