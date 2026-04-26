# Medical Documentation Assistant — Frontend

React 19 + Vite 8 + TypeScript, TanStack Router + Query, Tailwind v4, shadcn-style UI, i18n (RU/EN).

## Scripts

| Command | Description |
|--------|-------------|
| `npm run dev` | Dev server (port 5173), proxies `/api` → `VITE_PROXY_TARGET` (default `http://127.0.0.1:8000`) |
| `npm run build` | Typecheck + production build to `dist/` |
| `npm run preview` | Preview production build |
| `npm run lint` | ESLint |
| `npm run test` | Vitest unit tests |
| `npm run test:e2e` | Playwright (starts dev server) |
| `npm run gen:api` | Regenerate `src/shared/api/schema.gen.ts` (requires backend `/openapi.json`). Hand-written `schema.ts` remains the primary contract. |

## Site does not open (Yandex / Windows)

1. **Use** `http://127.0.0.1:5173` **instead of** `http://localhost:5173` (IPv4 only).
2. Restart dev server after `git pull` (`Ctrl+C`, then `npm run dev` again). The terminal must stay open; if it exits, the site will not load.
3. The dev server is configured with `server.host: true` so the address should work on your machine. If a corporate VPN/proxy rewrites `localhost`, disable it or add an exception.

## Environment

- `VITE_API_URL` — API origin (no trailing slash). Empty = use relative `/api/...` from the same host (Vite dev proxy in `vite.config.ts`).
- For codegen: `npm run gen:api` uses `VITE_API_URL` or `http://127.0.0.1:8000` for `openapi.json`.

## Docker

See repo root `docker-compose.yml` for an optional `frontend` static service (Nginx) building with `VITE_API_URL` pointing at the API service.
