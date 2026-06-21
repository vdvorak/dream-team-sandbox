import { defineConfig } from "vitest/config"

// Renderer logic (pure functions) is tested in a node environment — without Electron.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
})
