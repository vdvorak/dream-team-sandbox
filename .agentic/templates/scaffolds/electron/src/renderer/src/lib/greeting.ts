/// Pure function (no Electron/DOM) — a pattern for testable renderer logic.
export function greeting(name: string): string {
  const n = name.trim()
  return n ? `Hello, ${n}!` : "Hello!"
}
