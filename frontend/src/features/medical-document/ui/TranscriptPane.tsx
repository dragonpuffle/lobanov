import { useLayoutEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'

type Props = {
  text: string
  highlightStart: number | null
  highlightEnd: number | null
}

export function TranscriptPane({ text, highlightStart, highlightEnd }: Props) {
  const { t } = useTranslation()
  const markRef = useRef<HTMLSpanElement>(null)

  useLayoutEffect(() => {
    if (markRef.current && highlightStart != null) {
      markRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [highlightStart, highlightEnd])

  const before = highlightStart != null && highlightEnd != null ? text.slice(0, highlightStart) : text
  const mid =
    highlightStart != null && highlightEnd != null && highlightEnd > highlightStart ? text.slice(highlightStart, highlightEnd) : ''
  const after = highlightStart != null && highlightEnd != null ? text.slice(highlightEnd) : ''

  return (
    <div className="bg-muted/30 border-border flex min-h-0 flex-1 flex-col rounded-lg border">
      <div className="border-border flex items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-medium">{t('document.transcript')}</span>
        <span className="text-muted-foreground font-mono text-xs">{t('document.source')}</span>
      </div>
      <ScrollArea className="h-[min(60vh,520px)] p-3">
        {highlightStart != null && mid ? (
          <p className="font-mono text-sm leading-relaxed whitespace-pre-wrap">
            {before}
            <motion.span
              ref={markRef}
              layoutId="transcript-hl"
              className={cn('bg-primary/20 rounded-sm ring-1 ring-primary/30')}
            >
              {mid}
            </motion.span>
            {after}
          </p>
        ) : (
          <p className="font-mono text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        )}
      </ScrollArea>
    </div>
  )
}
