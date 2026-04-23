import { Link, useRouter } from '@tanstack/react-router'
import { FileText, LogOut, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuthStore } from '@/features/auth/model/authStore'
import { setLanguage } from '@/shared/i18n/i18n'

type Props = { title?: string }

export function AppHeader({ title }: Props) {
  const { t, i18n } = useTranslation()
  const router = useRouter()
  const { theme, setTheme } = useTheme()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const initials = user?.full_name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <header className="bg-card/80 border-border supports-[backdrop-filter]:bg-card/60 sticky top-0 z-40 w-full border-b backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-3">
          <Link to="/sessions" className="text-primary flex items-center gap-2 font-semibold">
            <FileText className="size-5" />
            {t('app.name')}
          </Link>
          {title ? <span className="text-muted-foreground hidden text-sm sm:inline">/ {title}</span> : null}
        </div>
        <nav className="flex items-center gap-1">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/sessions">{t('nav.sessions')}</Link>
          </Button>
          <Button variant="ghost" size="icon" asChild>
            <Link to="/settings" aria-label={t('nav.settings')}>
              <Settings className="size-4" />
            </Link>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative size-8 rounded-full">
                <Avatar className="size-8">
                  <AvatarFallback className="text-xs">{initials || '?'}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel className="truncate text-xs font-normal">{user?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setLanguage(i18n.language === 'ru' ? 'en' : 'ru')}>
                {i18n.language === 'ru' ? 'English' : 'Русский'}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  setTheme(theme === 'dark' ? 'light' : 'dark')
                }}
              >
                {theme === 'dark' ? t('settings.light') : t('settings.dark')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => {
                  logout()
                  void router.navigate({ to: '/login' })
                }}
                className="text-destructive"
              >
                <LogOut className="size-4" />
                {t('nav.logout')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
      </div>
    </header>
  )
}
