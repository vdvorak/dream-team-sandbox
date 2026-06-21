import { createResource, For, Show } from "solid-js"

import { apiClient } from "@/api/client"
import Dialog from "@/components/ui/Dialog"
import { t } from "@/i18n"

import styles from "./ExamplePage.module.css"

async function fetchExamples() {
  const { data } = await apiClient.GET("/examples")
  return data?.items ?? []
}

export default function ExamplePage() {
  const [examples] = createResource(fetchExamples)

  return (
    <div class={styles.page}>
      <header class={styles.header}>
        <h1 class={styles.title}>{t("example.title")}</h1>
        <Dialog triggerLabel={t("example.new")} title={t("example.newTitle")}>
          {/* Write form: createFormStore (components/createFormStore.ts) +
              *Field wrappers (components/ui/TextField.tsx). save(data, validate)
              calls apiClient.POST with the ?validate flag (rules §Write-flow). */}
          <p>Form: wire up createFormStore + TextField.</p>
        </Dialog>
      </header>
      <Show when={!examples.loading} fallback={<p>{t("example.loading")}</p>}>
        <ul class={styles.list}>
          <For each={examples()} fallback={<li>{t("example.empty")}</li>}>
            {(e) => <li class={styles.item}>{e.label}</li>}
          </For>
        </ul>
      </Show>
    </div>
  )
}
