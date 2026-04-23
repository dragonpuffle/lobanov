import createClient from 'openapi-fetch'
import type { paths } from '@/shared/api/schema'
import { API_BASE } from '@/shared/config/env'
import { getAccessToken, setTokenGetter } from '@/shared/api/token-bridge'

export { setTokenGetter }

export const api = createClient<paths>({ baseUrl: API_BASE })

api.use({
  onRequest({ request }) {
    const t = getAccessToken()
    if (t) request.headers.set('Authorization', `Bearer ${t}`)
    return request
  },
  onResponse({ response, request: req }) {
    if (response.status === 401 && !req.url.includes('/auth/login') && !req.url.includes('/auth/register')) {
      window.dispatchEvent(new CustomEvent('auth:logout', { detail: { reason: 'unauthorized' } }))
    }
    return response
  },
})
