import { useTranslation } from 'react-i18next'
import { AlertCircle, Check, HelpCircle, Pencil, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { FieldValueStatusStr } from '@/shared/api/types'
import { motion } from 'framer-motion'

const icons: Record<FieldValueStatusStr, typeof Check> = {
  auto_filled: Sparkles,
  user_edited: Pencil,
  missing: AlertCircle,
  doubtful: HelpCircle,
  confirmed: Check,
}

const variant: Record<FieldValueStatusStr, 'fieldAuto' | 'fieldUser' | 'fieldMissing' | 'fieldDoubt' | 'fieldConfirmed'> = {
  auto_filled: 'fieldAuto',
  user_edited: 'fieldUser',
  missing: 'fieldMissing',
  doubtful: 'fieldDoubt',
  confirmed: 'fieldConfirmed',
}

export function FieldStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  const s = (status in icons ? status : 'missing') as FieldValueStatusStr
  const I = icons[s]
  return (
    <motion.div layout initial={false} animate={{ scale: [1, 1.04, 1] }} transition={{ duration: 0.4 }}>
      <Badge variant={variant[s]} className="gap-1">
        <I className="size-3" />
        {t(`fieldStatus.${s}`)}
      </Badge>
    </motion.div>
  )
}
