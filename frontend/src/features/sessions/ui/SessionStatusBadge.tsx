import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import type { DocumentationSessionStatus } from '@/shared/api/types'

const s = cva('inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium', {
  variants: {
    status: {
      created: 'border-slate-200 bg-slate-100 text-slate-800',
      audio_uploaded: 'border-blue-200 bg-blue-50 text-blue-800',
      transcribed: 'border-violet-200 bg-violet-50 text-violet-800',
      facts_extracted: 'border-amber-200 bg-amber-50 text-amber-900',
      draft_created: 'border-teal-200 bg-teal-50 text-teal-900',
      confirmed: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    },
  },
  defaultVariants: { status: 'created' },
})

export function SessionStatusBadge({
  status,
  className,
}: { status: DocumentationSessionStatus } & React.ComponentProps<'span'>) {
  const { t } = useTranslation()
  return (
    <span className={cn(s({ status: status as VariantProps<typeof s>['status'] }), className)} title={status}>
      {t(`sessionStatus.${status}`, { defaultValue: status })}
    </span>
  )
}
