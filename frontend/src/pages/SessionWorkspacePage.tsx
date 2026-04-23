import { useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'framer-motion'
import { AppHeader } from '@/components/layout/AppHeader'
import { useSessionDetails } from '@/features/sessions/api/useSessions'
import { SessionStepper, computeWorkspaceStep } from '@/features/sessions/ui/SessionStepper'
import { useStartTranscription } from '@/features/transcription/api/useTranscription'
import { useGenerateDocument } from '@/features/medical-document/api/useMedicalDocument'
import { TranscriptionProgress } from '@/features/transcription/ui/TranscriptionProgress'
import { DocumentEditor } from '@/features/medical-document/ui/DocumentEditor'
import { AudioUploader } from '@/features/audio/ui/AudioUploader'
import { AudioRecorder } from '@/features/audio/ui/AudioRecorder'
import { uploadAudioFile } from '@/features/audio/lib/uploadAudioFile'
import { validateAudioFile } from '@/features/audio/lib/validateAudioFile'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { qk } from '@/shared/api/queryKeys'
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'
import { useMemo } from 'react'

export function SessionWorkspacePage() {
  const { t } = useTranslation()
  const { sessionId } = useParams({ strict: false })
  const sid = String(sessionId ?? '')
  const qc = useQueryClient()
  const { data: session, isLoading, isError } = useSessionDetails(sid || undefined)
  const transcribe = useStartTranscription()
  const gen = useGenerateDocument()

  const step = useMemo(() => (session ? computeWorkspaceStep(session) : 0), [session])
  const showAudio = session && !session.has_audio
  const showProcess = session && session.has_audio && !session.has_document
  const showDoc = session && session.has_document
  const readOnly = session?.status === 'confirmed'

  const invalidate = () => void qc.invalidateQueries({ queryKey: qk.session(sid) })

  if (isLoading) return <p className="p-4">…</p>
  if (isError || !session) return <p className="text-destructive p-4">Not found</p>

  return (
    <div className="min-h-dvh pb-32">
      <AppHeader title={t('nav.sessions')} />
      <main className="mx-auto max-w-6xl space-y-4 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/sessions">
              <ArrowLeft className="size-4" />
              {t('session.back')}
            </Link>
          </Button>
          <SessionStepper step={step} />
        </div>

        <AnimatePresence mode="wait">
          {showAudio ? (
            <motion.div key="audio" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>{t('session.stepAudio')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="up">
                    <TabsList>
                      <TabsTrigger value="up">{t('audio.upload')}</TabsTrigger>
                      <TabsTrigger value="rec">{t('audio.record')}</TabsTrigger>
                    </TabsList>
                    <TabsContent value="up">
                      <AudioUploader
                        sessionId={sid}
                        onUploaded={() => {
                          invalidate()
                        }}
                      />
                    </TabsContent>
                    <TabsContent value="rec">
                      <AudioRecorder
                        onRecorded={async (file) => {
                          const v = validateAudioFile(file)
                          if (!v.ok) {
                            toast.error(t(v.error === 'fileTooLarge' ? 'audio.fileTooLarge' : 'audio.invalidFormat'))
                            return
                          }
                          try {
                            await uploadAudioFile(sid, file, () => undefined)
                            toast.success('Uploaded')
                            invalidate()
                          } catch (e) {
                            toast.error(e instanceof Error ? e.message : 'Upload failed')
                          }
                        }}
                      />
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {showProcess ? (
          <motion.div
            key="process"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-muted/20 border-border space-y-4 rounded-xl border p-4"
            aria-live="polite"
          >
            <TranscriptionProgress session={session} />
            {session.has_audio && !session.has_transcript ? (
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  disabled={transcribe.isPending}
                  onClick={() => void transcribe.mutateAsync({ sessionId: sid, language: 'ru' }).then(invalidate)}
                >
                  {t('processing.transcribe')}
                </Button>
              </div>
            ) : null}
            {session.has_transcript && !session.has_document ? (
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  disabled={gen.isPending}
                  onClick={() => void gen.mutateAsync({ sessionId: sid, templateId: session.template_id }).then(invalidate)}
                >
                  {t('processing.generate')}
                </Button>
              </div>
            ) : null}
          </motion.div>
        ) : null}

        {showDoc ? (
          <DocumentEditor sessionId={sid} templateId={session.template_id} readOnly={readOnly} />
        ) : null}
      </main>
    </div>
  )
}
