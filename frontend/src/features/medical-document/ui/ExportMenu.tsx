import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useExportDocument } from '@/features/medical-document/api/useMedicalDocument'
import { toast } from 'sonner'

type Props = { sessionId: string; disabled?: boolean }

export function ExportMenu({ sessionId, disabled }: Props) {
  const { t } = useTranslation()
  const exp = useExportDocument()
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button size="sm" variant="outline" disabled={disabled || exp.isPending}>
          <Download className="size-4" />
          {t('document.export')}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Format</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {(['json', 'pdf'] as const).map((fmt) => (
          <DropdownMenuItem
            key={fmt}
            onSelect={() => {
              void exp.mutateAsync({ sessionId, format: fmt }).then((d) => {
                toast.success(d?.message ?? 'Exported', { description: d?.task_id })
              })
            }}
          >
            {fmt.toUpperCase()}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
