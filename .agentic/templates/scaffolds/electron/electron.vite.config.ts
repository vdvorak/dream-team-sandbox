import { defineConfig, externalizeDepsPlugin } from "electron-vite"
import solid from "vite-plugin-solid"

// Three build targets: main (Node), preload (bridge), renderer (SolidJS — like the web scaffold).
export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
  },
  renderer: {
    plugins: [solid()],
  },
})
