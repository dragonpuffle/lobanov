import { useTranslation } from 'react-i18next'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

const steps = ['audio', 'process', 'doc', 'done'] as const
type Key = (typeof steps)[number]

export function computeWorkspaceStep(s: { status: string; has_audio: boolean; has_transcript: boolean; has_document: boolean }) {
  if (s.status === 'confirmed') return 3
  if (s.has_document) return 2
  if (s.has_audio || s.has_transcript) return 1
  return 0
}

export function SessionStepper({ step }: { step: number }) {
  const { t } = useTranslation()
  const active = Math.min(3, Math.max(0, step))
  const labels: Record<Key, string> = {
    audio: t('session.stepAudio'),
    process: t('session.stepProcess'),
    doc: t('session.stepDoc'),
    done: t('session.stepDone'),
  }
  return (
    <ol className="flex flex-wrap items-center gap-1 text-xs sm:gap-2 sm:text-sm" aria-label="Session progress">
      {steps.map((key, i) => (
        <li key={key} className="flex items-center gap-1 sm:gap-2">
          <span
            className={cn(
              'border-border flex size-6 items-center justify-center rounded-full border text-xs font-medium',
              i < active && 'bg-primary/15 text-primary border-primary/30',
              i === active && 'bg-primary text-primary-foreground border-primary',
              i > active && 'text-muted-foreground',
            )}
          >
            {i < active ? <Check className="size-3.5" /> : i + 1}
          </span>
          <span className={cn('hidden sm:inline', i > active && 'text-muted-foreground')}>{labels[key]}</span>
          {i < steps.length - 1 ? <span className="text-muted-foreground hidden px-0.5 sm:inline">—</span> : null}
        </li>
      ))}
    </ol>
  )
}
