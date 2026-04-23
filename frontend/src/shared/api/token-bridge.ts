/** Decoupled token access for the HTTP client (avoids import cycles with auth store). */
let getToken: (() => string | null) | null = null

export function setTokenGetter(fn: () => string | null) {
  getToken = fn
}

export function getAccessToken() {
  return getToken?.() ?? null
}
