import { useTranslation } from 'react-i18next'
import { Check, Circle, Loader2 } from 'lucide-react'
import type { SessionDetailsResponse } from '@/shared/api/types'

type Props = {
  session: SessionDetailsResponse
  /** Spinner on “transcribing” only after the user started the job (or while the start request is in flight). */
  transcriptionInProgress?: boolean
}

export function TranscriptionProgress({ session, transcriptionInProgress = false }: Props) {
  const { t } = useTranslation()
  const a = session.has_audio
  const tr = session.has_transcript
  const doc = session.has_document
  const transcribingActive = Boolean(transcriptionInProgress && a && !tr)
  return (
    <ol className="max-w-md space-y-3" aria-live="polite">
      <li className="flex items-center gap-2">
        {a ? <Check className="text-field-confirmed size-5" /> : <Circle className="text-muted-foreground size-5" />}
        <span>Audio</span>
      </li>
      <li className="flex items-center gap-2">
        {tr ? (
          <Check className="text-field-confirmed size-5" />
        ) : transcribingActive ? (
          <Loader2 className="text-primary size-5 animate-spin" />
        ) : (
          <Circle className="text-muted-foreground size-5" />
        )}
        <span>{t('processing.transcribing')}</span>
      </li>
      <li className="flex items-center gap-2">
        {doc ? <Check className="text-field-confirmed size-5" /> : <Circle className="text-muted-foreground size-5" />}
        <span>{t('processing.generating')}</span>
      </li>
    </ol>
  )
}
