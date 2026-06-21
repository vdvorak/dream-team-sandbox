import createClient from "openapi-fetch"

import { accessToken } from "@/auth/tokenStore"

import type { paths } from "./schema"

// Typed API client. Inputs/outputs defined by the schema; treat the output as untrusted.
export const apiClient = createClient<paths>({ baseUrl: "/api/v1" })

// Authorization header automatically on every request — pages never set it manually.
apiClient.use({
  onRequest({ request }) {
    const token = accessToken()
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`)
    }
    return request
  },
})
