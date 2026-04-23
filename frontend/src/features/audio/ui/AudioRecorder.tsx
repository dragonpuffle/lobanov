import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { Mic, Square } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useMediaRecorder } from '@/features/audio/lib/useMediaRecorder'
import { WaveformPlayer } from '@/features/audio/ui/WaveformPlayer'
import { validateAudioFile } from '@/features/audio/lib/validateAudioFile'

type Props = { onRecorded: (file: File) => void }

export function AudioRecorder({ onRecorded }: Props) {
  const { t } = useTranslation()
  const { start, stop, recording, error } = useMediaRecorder()
  const [url, setUrl] = useState<string | null>(null)
  const [ticker, setTicker] = useState(0)
  const tref = useRef<number | null>(null)

  useEffect(() => {
    if (recording) {
      const t0 = Date.now()
      tref.current = window.setInterval(() => setTicker(Math.floor((Date.now() - t0) / 1000)), 500)
    } else {
      if (tref.current) clearInterval(tref.current)
    }
    return () => {
      if (tref.current) clearInterval(tref.current)
    }
  }, [recording])

  return (
    <div className="space-y-4">
      {error ? <p className="text-destructive text-sm">{error}</p> : null}
      <div className="flex items-center justify-center gap-4">
        <motion.div
          className="relative"
          animate={recording ? { scale: [1, 1.08, 1] } : {}}
          transition={{ duration: 1.2, repeat: recording ? Infinity : 0 }}
        >
          <Button
            type="button"
            size="lg"
            variant={recording ? 'destructive' : 'default'}
            className="size-20 rounded-full"
            onClick={async () => {
              if (recording) {
                const f = await stop()
                if (f) {
                  const v = validateAudioFile(f)
                  if (v.ok) {
                    onRecorded(f)
                    setUrl(URL.createObjectURL(f))
                  }
                }
              } else {
                setUrl(null)
                await start()
              }
            }}
          >
            {recording ? <Square className="size-6" /> : <Mic className="size-8" />}
          </Button>
        </motion.div>
        <div>
          <p className="text-lg font-mono tabular-nums">
            {Math.floor(ticker / 60)
              .toString()
              .padStart(2, '0')}
            :{(ticker % 60).toString().padStart(2, '0')}
          </p>
          <p className="text-muted-foreground text-sm">{recording ? t('audio.recording') : t('audio.record')}</p>
        </div>
      </div>
      {url ? <WaveformPlayer url={url} /> : null}
    </div>
  )
}
