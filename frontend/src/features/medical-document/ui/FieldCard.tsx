import { useId, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'framer-motion'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { FieldStatusBadge } from '@/features/medical-document/ui/FieldStatusBadge'
import { useUpdateField } from '@/features/medical-document/api/useMedicalDocument'
import type { FieldValueDTO } from '@/shared/api/types'
import { Button } from '@/components/ui/button'
import { Link2 } from 'lucide-react'

type Props = {
  sessionId: string
  field: FieldValueDTO
  fieldType: 'text' | 'number' | 'date' | 'select' | 'textarea' | 'unknown'
  options?: string[] | null
  readOnly: boolean
  onHighlight: (f: FieldValueDTO) => void
}

export function FieldCard({ sessionId, field, fieldType, options, readOnly, onHighlight }: Props) {
  const { t } = useTranslation()
  const update = useUpdateField(sessionId)
  const [editing, setEditing] = useState(false)
  const uid = useId()
  const f = useForm({ defaultValues: { value: field.value ?? '' } })

  const save = f.handleSubmit((data) => {
    if (readOnly) return
    void update.mutateAsync({ fieldId: field.field_id, value: data.value }, { onSuccess: () => setEditing(false) })
  })

  return (
    <Card className="scroll-mt-32">
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0 pb-2">
        <div>
          <h4 className="text-sm font-medium">
            {field.field_label}
            {field.is_required ? <span className="text-destructive"> *</span> : null}
          </h4>
          <p className="text-muted-foreground text-xs">{field.field_name}</p>
        </div>
        <FieldStatusBadge status={field.status} />
      </CardHeader>
      <CardContent className="space-y-2">
        {editing && !readOnly ? (
          <form
            onSubmit={save}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setEditing(false)
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && (fieldType === 'textarea' || fieldType === 'text')) {
                e.preventDefault()
                void save()
              }
            }}
            className="space-y-2"
          >
            {fieldType === 'textarea' || (fieldType === 'unknown' && field.field_name.match(/history|complaint|plan|exam/i)) ? (
              <Textarea id={uid} rows={4} {...f.register('value')} />
            ) : fieldType === 'select' && options?.length ? (
              <Select
                value={f.watch('value')}
                onValueChange={(v) => f.setValue('value', v, { shouldDirty: true })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {options.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : fieldType === 'date' ? (
              <Input id={uid} type="date" {...f.register('value')} />
            ) : fieldType === 'number' ? (
              <Input id={uid} type="number" {...f.register('value')} />
            ) : (
              <Input id={uid} {...f.register('value')} />
            )}
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={update.isPending}>
                Save
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>
                Cancel
              </Button>
            </div>
          </form>
        ) : (
          <div
            role="button"
            tabIndex={0}
            onClick={() => {
              onHighlight(field)
              if (!readOnly) setEditing(true)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                onHighlight(field)
                if (!readOnly) setEditing(true)
              }
            }}
            className="hover:bg-muted/50 cursor-pointer rounded-md p-2"
          >
            <p className="min-h-8 text-sm whitespace-pre-wrap">{field.value || '—'}</p>
            <AnimatePresence>
              {field.source_text ? (
                <motion.blockquote
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="text-muted-foreground border-primary/20 mt-2 border-l-2 pl-2 text-xs italic"
                >
                  {field.source_text}
                </motion.blockquote>
              ) : null}
            </AnimatePresence>
          </div>
        )}
        {field.source_start_index != null && field.source_text ? (
          <Button type="button" variant="link" className="h-auto p-0 text-xs" onClick={() => onHighlight(field)}>
            <Link2 className="size-3" />
            {t('document.showInTranscript')}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}
