import { createSignal, onCleanup, onMount, Show } from "solid-js"

import { t } from "@/i18n"

import styles from "./BackendStatusBanner.module.css"

// Global backend-unavailable indicator on every route
// (rules/frontend.md §Backend availability indicator). Unavailable = network error
// or 5xx. Active polling probe; does not block interaction (no overlay).
export default function BackendStatusBanner() {
  const [down, setDown] = createSignal(false)
  let timer: ReturnType<typeof setInterval> | undefined

  const probe = async () => {
    try {
      const res = await fetch("/api/v1/health")
      setDown(res.status >= 500)
    } catch {
      setDown(true)
    }
  }

  onMount(() => {
    void probe()
    timer = setInterval(() => void probe(), 15000)
  })
  onCleanup(() => clearInterval(timer))

  return (
    <Show when={down()}>
      <div class={styles.banner} role="status">
        {t("backend.unavailable")}
      </div>
    </Show>
  )
}
