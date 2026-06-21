import i18next from "i18next"

import cs from "./locales/cs.json"
import en from "./locales/en.json"

// i18n from the first line (constitution §Lokalizace). CS is the default locale.
// Resources inline → init is synchronous; `t()` works right after import.
void i18next.init({
  lng: "cs",
  fallbackLng: "cs",
  resources: { cs: { translation: cs }, en: { translation: en } },
  interpolation: { escapeValue: false },
  returnNull: false,
})

// Helper for components: `t("key")`. No user-facing text literal outside locales.
export const t = (key: string, opts?: Record<string, unknown>): string => i18next.t(key, opts)

export { i18next }
