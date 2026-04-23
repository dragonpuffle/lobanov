import { useEffect, useRef } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { cn } from '@/lib/utils'

type Props = { url: string; className?: string; height?: number }

export function WaveformPlayer({ url, className, height = 64 }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const ws = useRef<WaveSurfer | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const w = WaveSurfer.create({
      container: ref.current,
      height,
      waveColor: 'oklch(0.5 0.12 195)',
      progressColor: 'oklch(0.45 0.15 255)',
      cursorWidth: 1,
    })
    void w.load(url)
    ws.current = w
    return () => {
      w.destroy()
      ws.current = null
    }
  }, [url, height])

  return <div ref={ref} className={cn('w-full overflow-hidden rounded-md', className)} />
}
