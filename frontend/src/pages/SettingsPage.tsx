import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import { AppHeader } from '@/components/layout/AppHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { setLanguage } from '@/shared/i18n/i18n'

export function SettingsPage() {
  const { t, i18n } = useTranslation()
  const { theme, setTheme } = useTheme()

  return (
    <div className="min-h-dvh">
      <AppHeader title={t('settings.title')} />
      <main className="mx-auto max-w-xl space-y-6 p-4">
        <Card>
          <CardHeader>
            <CardTitle>{t('settings.theme')}</CardTitle>
            <CardDescription>Light / dark / system</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {(['light', 'dark', 'system'] as const).map((th) => (
              <Button key={th} variant={theme === th ? 'default' : 'outline'} size="sm" onClick={() => setTheme(th)}>
                {t(`settings.${th}` as 'settings.light' | 'settings.dark' | 'settings.system')}
              </Button>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{t('settings.language')}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button variant={i18n.language === 'en' ? 'default' : 'outline'} size="sm" onClick={() => setLanguage('en')}>
              English
            </Button>
            <Button variant={i18n.language === 'ru' ? 'default' : 'outline'} size="sm" onClick={() => setLanguage('ru')}>
              Русский
            </Button>
          </CardContent>
        </Card>
        <p className="text-muted-foreground text-sm">JWT and profile are managed from the header menu.</p>
      </main>
    </div>
  )
}
