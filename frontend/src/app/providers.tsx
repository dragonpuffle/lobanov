import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { I18nextProvider } from 'react-i18next'
import { ThemeProvider } from 'next-themes'
import { Toaster } from 'sonner'
import i18n from '@/shared/i18n/i18n'
import { setTokenGetter } from '@/shared/api/token-bridge'
import { useAuthStore } from '@/features/auth/model/authStore'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function AuthSync() {
  const logout = useAuthStore((s) => s.logout)
  useEffect(() => {
    setTokenGetter(() => useAuthStore.getState().accessToken)
  }, [])

  useEffect(() => {
    const onLogout = () => {
      logout()
      const p = window.location.pathname
      if (p !== '/login' && p !== '/register' && p !== '/') {
        window.location.assign('/login')
      }
    }
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [logout])

  return null
}

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={qc}>
      <I18nextProvider i18n={i18n}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <AuthSync />
          {children}
          <Toaster richColors position="bottom-right" closeButton />
        </ThemeProvider>
      </I18nextProvider>
    </QueryClientProvider>
  )
}
