import { createSignal } from "solid-js"

// The access token lives in a signal OUTSIDE AuthContext so `client.ts` can read it without
// a circular dependency (client ← tokenStore, AuthContext ← tokenStore). Protected pages
// NEVER set Authorization manually — the middleware in client.ts handles it.
const [accessToken, setAccessToken] = createSignal<string | null>(null)

export { accessToken, setAccessToken }
