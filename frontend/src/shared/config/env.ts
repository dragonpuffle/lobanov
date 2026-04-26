/**
 * API origin (no trailing slash). Empty = same-origin, paths begin with `/api/v1/...` (Vite dev: serve app + relative API or proxy).
 * Set `VITE_API_URL=http://127.0.0.1:8000` if the API is on another origin.
 */
export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''
