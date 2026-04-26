import { tanstackRouter } from '@tanstack/router-plugin/vite'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [tanstackRouter(), tailwindcss(), react()],
  resolve: {
    alias: {
      '@': path.join(root, 'src'),
    },
  },
  server: {
    // `localhost` on Windows may resolve to IPv6 (::1) first; default bind is IPv4-only and the browser
    // (notably Yandex) then shows a generic "page not found" instead of connection errors.
    host: true, // listen on 0.0.0.0; use http://127.0.0.1:5173 if you prefer not to expose LAN
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
