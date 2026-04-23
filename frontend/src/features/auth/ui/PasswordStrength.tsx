import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

const rules = (pwd: string) => ({
  len: pwd.length >= 8,
  upper: /[A-Z]/.test(pwd),
  lower: /[a-z]/.test(pwd),
  num: /[0-9]/.test(pwd),
  spec: /[^A-Za-z0-9]/.test(pwd),
})

export function usePasswordScore(password: string) {
  return useMemo(() => {
    const r = rules(password)
    const passed = [r.len, r.upper, r.lower, r.num, r.spec].filter(Boolean).length
    return { passed, total: 5, r }
  }, [password])
}

export function PasswordStrength({ password }: { password: string }) {
  const { t } = useTranslation()
  const { passed, total } = usePasswordScore(password)
  const pct = (passed / total) * 100
  if (!password) return null
  return (
    <div className="space-y-1.5">
      <Progress value={pct} className="h-1" />
      <p className={cn('text-muted-foreground text-xs', passed < 5 && 'text-amber-600')}>{t('auth.weakPassword')}</p>
    </div>
  )
}
