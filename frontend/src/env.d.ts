/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_REQUEST_TIMEOUT_MS?: string
  readonly VITE_POLL_INTERVAL_MS?: string
  readonly VITE_MAX_IMAGE_SIZE_MB?: string
  readonly VITE_DEFAULT_LOCALE?: string
  readonly VITE_DISPLAY_TIME_ZONE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
