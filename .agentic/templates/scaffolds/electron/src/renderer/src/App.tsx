import { createSignal, onMount } from "solid-js"

import { greeting } from "./lib/greeting"

// Example: the renderer calls the main process ONLY through the typed preload bridge (window.api).
// Take real UI patterns (Kobalte + tokens + CSS Modules) from the solidjs scaffold.
export function App() {
  const [version, setVersion] = createSignal("…")
  onMount(async () => setVersion(await window.api.getVersion()))
  return (
    <main>
      <h1>{greeting("desktop")}</h1>
      <p>App version (from the main process): {version()}</p>
    </main>
  )
}
