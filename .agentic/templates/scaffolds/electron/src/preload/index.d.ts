import type { Api } from "./index"

// The renderer sees the bridge as a typed `window.api` (no `any`).
declare global {
  interface Window {
    api: Api
  }
}
