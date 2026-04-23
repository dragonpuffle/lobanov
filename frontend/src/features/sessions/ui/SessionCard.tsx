import { Link } from '@tanstack/react-router'
import { FileAudio, FileText, Mic } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { SessionStatusBadge } from '@/features/sessions/ui/SessionStatusBadge'
import type { SessionResponse } from '@/shared/api/types'
import { cn } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { qk } from '@/shared/api/queryKeys'

type Props = { session: SessionResponse }

export function SessionCard({ session }: Props) {
  const { t } = useTranslation()
  const { data: tMeta } = useQuery({
    queryKey: qk.template(session.template_id),
    queryFn: async () => {
      const { data } = await api.GET('/api/v1/templates/{template_id}', {
        params: { path: { template_id: session.template_id } },
      })
      return data
    },
  })
  return (
    <Link to="/sessions/$sessionId" params={{ sessionId: session.id }}>
      <Card className="hover:border-primary/40 group transition-all hover:shadow-md">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 font-medium">{tMeta?.name ?? t('session.template')}</h3>
            <SessionStatusBadge status={session.status} />
          </div>
          <p className="text-muted-foreground text-xs">
            {new Date(session.created_at).toLocaleString()} · {session.id.slice(0, 8)}…
          </p>
        </CardHeader>
        <CardContent className="text-muted-foreground flex gap-3 text-xs">
          <span className={cn('flex items-center gap-1', session.status !== 'created' && 'text-primary')}>
            <FileAudio className="size-3.5" /> audio
          </span>
          <span className={cn('flex items-center gap-1', ['transcribed', 'facts_extracted', 'draft_created', 'confirmed'].includes(session.status) && 'text-primary')}>
            <Mic className="size-3.5" /> stt
          </span>
          <span className={cn('flex items-center gap-1', ['draft_created', 'confirmed'].includes(session.status) && 'text-primary')}>
            <FileText className="size-3.5" /> doc
          </span>
        </CardContent>
      </Card>
    </Link>
  )
}
