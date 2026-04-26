import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import type { ValidateDocumentResponse } from '@/shared/api/types'

type Props = {
  validation: ValidateDocumentResponse
  onJumpToField: (name: string) => void
  onConfirm: () => void
  canConfirm: boolean
  readOnly: boolean
}

export function ValidationSummaryBar({ validation, onJumpToField, onConfirm, canConfirm, readOnly }: Props) {
  const { t } = useTranslation()
  const { is_valid, missing_fields, doubtful_fields, required_fields_count, filled_fields_count } = validation
  return (
    <div
      role="status"
      className="bg-card/95 border-border fixed right-0 bottom-0 left-0 z-30 border-t p-3 shadow-lg backdrop-blur"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm">
          <p className={is_valid ? 'text-field-confirmed font-medium' : 'text-amber-600'}>
            {t('document.validate')}: {filled_fields_count} / {required_fields_count} required
          </p>
          <div className="text-muted-foreground mt-1 flex flex-wrap gap-1">
            {missing_fields.map((n) => (
              <Button key={n} type="button" variant="link" className="h-auto p-0 text-xs" onClick={() => onJumpToField(n)}>
                {n} (missing)
              </Button>
            ))}
            {doubtful_fields.map((n) => (
              <Button key={n} type="button" variant="link" className="h-auto p-0 text-xs" onClick={() => onJumpToField(n)}>
                {n} (?)
              </Button>
            ))}
          </div>
        </div>
        {!readOnly ? (
          <Button disabled={!canConfirm} onClick={onConfirm}>
            {t('document.confirm')}
          </Button>
        ) : null}
      </div>
    </div>
  )
}
