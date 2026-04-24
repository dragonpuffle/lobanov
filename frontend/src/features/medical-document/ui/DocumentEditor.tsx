import { useCallback, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'framer-motion'
import { useMedicalDocument, useValidateDocument, useConfirmDocument } from '@/features/medical-document/api/useMedicalDocument'
import { useTemplateDetails } from '@/features/templates/api/useTemplates'
import { TranscriptPane } from '@/features/medical-document/ui/TranscriptPane'
import { FieldCard } from '@/features/medical-document/ui/FieldCard'
import { ValidationSummaryBar } from '@/features/medical-document/ui/ValidationSummaryBar'
import { ExportMenu } from '@/features/medical-document/ui/ExportMenu'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMediaQuery } from '@/shared/hooks/useMediaQuery'
import type { FieldValueDTO } from '@/shared/api/types'
import { toast } from 'sonner'

type Props = { sessionId: string; templateId: string; readOnly: boolean }

function guessFieldType(name: string): 'text' | 'textarea' {
  if (/history|complaint|plan|exam|diagnos|treat/i.test(name)) return 'textarea'
  return 'text'
}

export function DocumentEditor({ sessionId, templateId, readOnly }: Props) {
  const { t } = useTranslation()
  const { data: doc, isLoading, error: docError } = useMedicalDocument(sessionId)
  const { data: val } = useValidateDocument(sessionId)
  const { data: template } = useTemplateDetails(templateId)
  const confirmM = useConfirmDocument()
  const [hl, setHl] = useState<{ start: number | null; end: number | null }>({ start: null, end: null })
  const [selected, setSelected] = useState<FieldValueDTO | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const fieldRefs = useRef<Record<string, HTMLDivElement | null>>({})

  const onHighlight = useCallback(
    (f: FieldValueDTO) => {
      setSelected(f)
      if (f.source_start_index != null && f.source_end_index != null) {
        setHl({ start: f.source_start_index, end: f.source_end_index })
      } else {
        setHl({ start: null, end: null })
      }
    },
    [],
  )

  const jump = useCallback(
    (name: string) => {
      const f = doc?.field_values.find((x) => x.field_name === name)
      if (f) onHighlight(f)
      fieldRefs.current[name]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },
    [doc?.field_values, onHighlight],
  )

  if (isLoading) return <p className="p-4">Loading document…</p>
  if (docError || !doc) return <p className="text-destructive p-4">No document. Generate it from the previous step.</p>
  if (!val) return <p className="p-4">Loading validation…</p>

  const fieldsByName = new Map(template?.fields.map((x) => [x.name, x]) ?? [])

  const editorBody = (
    <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">
      <TranscriptPane
        text={doc.transcript_text}
        highlightStart={selected ? hl.start : null}
        highlightEnd={selected ? hl.end : null}
      />
      <div className="space-y-3">
        <h2 className="text-lg font-medium">{doc.template_name}</h2>
        {doc.status === 'confirmed' ? <p className="text-muted-foreground text-sm">{t('document.readOnly')}</p> : null}
        {doc.field_values
          .slice()
          .sort((a, b) => {
            const oa = fieldsByName.get(a.field_name)?.order ?? 0
            const ob = fieldsByName.get(b.field_name)?.order ?? 0
            return oa - ob
          })
          .map((f) => {
            const meta = fieldsByName.get(f.field_name)
            const opts = meta?.options && typeof meta.options === 'object' && Array.isArray((meta.options as { options?: string[] }).options) ? (meta.options as { options: string[] }).options : (meta?.options as string[] | null)
            return (
              <div
                key={f.field_id}
                ref={(el) => {
                  fieldRefs.current[f.field_name] = el
                }}
              >
                <FieldCard
                  sessionId={sessionId}
                  field={f}
                  fieldType={meta?.name ? guessFieldType(meta.name) : 'unknown'}
                  options={Array.isArray(opts) ? opts : null}
                  readOnly={readOnly}
                  onHighlight={onHighlight}
                />
              </div>
            )
          })}
      </div>
    </div>
  )

  return (
    <>
      <div className="mb-2 flex items-center justify-end gap-2">
        <ExportMenu sessionId={sessionId} disabled={doc.status !== 'confirmed'} />
      </div>
      <AnimatePresence mode="wait">
        {isDesktop ? (
          <motion.div key="split" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex min-h-0 flex-1 flex-col">
            {editorBody}
          </motion.div>
        ) : (
          <Tabs defaultValue="doc" className="min-h-0 flex-1">
            <TabsList>
              <TabsTrigger value="t">{t('document.transcript')}</TabsTrigger>
              <TabsTrigger value="doc">{t('document.fields')}</TabsTrigger>
            </TabsList>
            <TabsContent value="t" className="min-h-0">
              <TranscriptPane
                text={doc.transcript_text}
                highlightStart={selected ? hl.start : null}
                highlightEnd={selected ? hl.end : null}
              />
            </TabsContent>
            <TabsContent value="doc" className="min-h-0 space-y-3">
              {doc.field_values.map((f) => (
                <div
                  key={f.field_id}
                  ref={(el) => {
                    fieldRefs.current[f.field_name] = el
                  }}
                >
                  <FieldCard
                    sessionId={sessionId}
                    field={f}
                    fieldType="unknown"
                    readOnly={readOnly}
                    onHighlight={onHighlight}
                  />
                </div>
              ))}
            </TabsContent>
          </Tabs>
        )}
      </AnimatePresence>
      {!readOnly ? (
        <ValidationSummaryBar
          validation={val}
          onJumpToField={jump}
          onConfirm={() => setConfirmOpen(true)}
          canConfirm={val.is_valid}
          readOnly={readOnly}
        />
      ) : null}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('document.confirm')}</DialogTitle>
            <DialogDescription>Irreversible for this session workflow. Required fields: {val.filled_fields_count}/{val.required_fields_count}.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                void confirmM.mutateAsync(sessionId).then(() => {
                  setConfirmOpen(false)
                  toast.success('Confirmed')
                })
              }}
            >
              {t('document.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
