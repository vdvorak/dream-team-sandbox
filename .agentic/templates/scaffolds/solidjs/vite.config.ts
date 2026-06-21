import { defineConfig } from "vitest/config"
import solid from "vite-plugin-solid"
import { resolve } from "node:path"

export default defineConfig({
  plugins: [solid()],
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
})
