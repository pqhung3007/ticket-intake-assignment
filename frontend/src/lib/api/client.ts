import createClient, { type Middleware } from 'openapi-fetch'

import { ApiError } from './errors'
import type { paths } from './schema.gen'

/** Turn non-2xx responses into ApiError so TanStack Query sees a rejected promise. */
const throwOnError: Middleware = {
  async onResponse({ response }) {
    if (response.ok) return response
    let code = 'http_error'
    let message = `Request failed (${response.status})`
    let details: unknown
    try {
      const body = (await response.clone().json()) as {
        error?: { code?: string; message?: string; details?: unknown }
      }
      code = body.error?.code ?? code
      message = body.error?.message ?? message
      details = body.error?.details
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, code, message, details)
  },
}

export const api = createClient<paths>({ baseUrl: '', credentials: 'same-origin' })
api.use(throwOnError)

/** openapi-fetch returns {data, error}; with throwOnError, data is always present on success. */
export function unwrap<T>(result: { data?: T }): T {
  if (result.data === undefined) throw new ApiError(500, 'empty_response', 'Empty response from server')
  return result.data
}
