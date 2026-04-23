import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useTranslation } from 'react-i18next'
import { Upload } from 'lucide-react'
import { motion } from 'framer-motion'
import { validateAudioFile } from '@/features/audio/lib/validateAudioFile'
import { uploadAudioFile } from '@/features/audio/lib/uploadAudioFile'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { WaveformPlayer } from '@/features/audio/ui/WaveformPlayer'
import { toast } from 'sonner'

type Props = {
  sessionId: string
  onUploaded: () => void
}

export function AudioUploader({ sessionId, onUploaded }: Props) {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [loading, setLoading] = useState(false)

  const onDrop = useCallback(
    (accepted: File[]) => {
      const f = accepted[0]
      if (!f) return
      const v = validateAudioFile(f)
      if (!v.ok) {
        toast.error(t(v.error === 'fileTooLarge' ? 'audio.fileTooLarge' : 'audio.invalidFormat'))
        return
      }
      setFile(f)
      setPreview(URL.createObjectURL(f))
    },
    [t],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: { 'audio/*': [] },
  })

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          'border-border bg-muted/20 hover:border-primary/50 cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors',
          isDragActive && 'border-primary bg-primary/5',
        )}
      >
        <input {...getInputProps()} />
        <Upload className="text-muted-foreground mx-auto size-10" />
        <p className="mt-2 font-medium">{t('audio.drop')}</p>
      </div>
      {file && preview ? (
        <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
          <p className="text-muted-foreground text-sm">
            {file.name} — {(file.size / 1024 / 1024).toFixed(2)} MB
          </p>
          <WaveformPlayer url={preview} />
          {loading ? <Progress value={progress} /> : null}
          <Button
            type="button"
            disabled={loading}
            onClick={async () => {
              if (!file) return
              setLoading(true)
              setProgress(0)
              try {
                await uploadAudioFile(sessionId, file, setProgress)
                toast.success('Uploaded')
                onUploaded()
              } catch (e) {
                toast.error(e instanceof Error ? e.message : 'Upload error')
              } finally {
                setLoading(false)
              }
            }}
          >
            {t('audio.upload')}
          </Button>
        </motion.div>
      ) : null}
    </div>
  )
}
