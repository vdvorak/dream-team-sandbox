import { describe, expect, it } from "vitest"

import { greeting } from "./greeting"

describe("greeting", () => {
  it("greets by name", () => {
    expect(greeting("desktop")).toBe("Hello, desktop!")
  })

  it("falls back without a name", () => {
    expect(greeting("   ")).toBe("Hello!")
  })
})
