import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AppHeader } from '@/components/layout/AppHeader'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSessions } from '@/features/sessions/api/useSessions'
import { SessionCard } from '@/features/sessions/ui/SessionCard'
import { NewSessionDialog } from '@/features/sessions/ui/NewSessionDialog'
import { Skeleton } from '@/components/ui/skeleton'
import type { DocumentationSessionStatus } from '@/shared/api/types'

const statuses: (DocumentationSessionStatus | 'all')[] = [
  'all',
  'created',
  'audio_uploaded',
  'transcribed',
  'facts_extracted',
  'draft_created',
  'confirmed',
]

export function SessionsListPage() {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [st, setSt] = useState<(typeof statuses)[number]>('all')
  const filters = useMemo(
    () => ({
      limit: 100,
      offset: 0,
      status: st === 'all' ? undefined : st,
    }),
    [st],
  )
  const { data, isLoading, isError } = useSessions(filters)
  const filtered = useMemo(() => {
    if (!data?.sessions) return []
    if (!q.trim()) return data.sessions
    const low = q.toLowerCase()
    return data.sessions.filter((s) => s.id.toLowerCase().includes(low) || s.template_id.toLowerCase().includes(low))
  }, [data?.sessions, q])

  return (
    <div className="min-h-dvh">
      <AppHeader title={t('sessions.title')} />
      <main className="mx-auto max-w-6xl space-y-6 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">{t('sessions.title')}</h1>
          <div className="flex flex-1 flex-wrap items-center justify-end gap-2">
            <Input
              placeholder={t('sessions.search')}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="max-w-xs"
            />
            <Select value={st} onValueChange={(v) => setSt(v as (typeof statuses)[number])}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder={t('sessions.filterStatus')} />
              </SelectTrigger>
              <SelectContent>
                {statuses.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s === 'all' ? t('sessions.allStatuses') : s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <NewSessionDialog />
          </div>
        </div>
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-36 w-full" />
            ))}
          </div>
        ) : isError ? (
          <p className="text-destructive">Failed to load</p>
        ) : filtered.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-xl border border-dashed p-12 text-center">
            {t('sessions.empty')}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {filtered.map((s) => (
              <SessionCard key={s.id} session={s} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
