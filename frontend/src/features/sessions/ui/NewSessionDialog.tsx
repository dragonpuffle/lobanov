import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useTemplates } from '@/features/templates/api/useTemplates'
import { useCreateSession } from '@/features/sessions/api/useCreateSession'
import { Skeleton } from '@/components/ui/skeleton'
import { Card } from '@/components/ui/card'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

export function NewSessionDialog() {
  const { t } = useTranslation()
  const router = useRouter()
  const { data, isLoading } = useTemplates(true)
  const create = useCreateSession()
  const [open, setOpen] = useState(false)
  const [sel, setSel] = useState<string | null>(null)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">{t('sessions.new')}</Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg" showClose>
        <DialogHeader>
          <DialogTitle>{t('sessions.new')}</DialogTitle>
          <DialogDescription>Choose a medical document template for this session.</DialogDescription>
        </DialogHeader>
        <div className="max-h-72 space-y-2 overflow-y-auto">
          {isLoading
            ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)
            : data?.templates.map((tm) => (
                <button
                  key={tm.id}
                  type="button"
                  onClick={() => setSel(tm.id)}
                  className={cn('w-full text-left', sel === tm.id && 'ring-primary ring-2 ring-offset-2')}
                >
                  <Card className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{tm.name}</p>
                        <p className="text-muted-foreground line-clamp-2 text-sm">{tm.description}</p>
                        <p className="text-muted-foreground mt-1 text-xs">v{tm.version}</p>
                      </div>
                      {sel === tm.id ? <Check className="text-primary size-5 shrink-0" /> : null}
                    </div>
                  </Card>
                </button>
              ))}
        </div>
        <DialogFooter>
          <Button
            disabled={!sel || create.isPending}
            onClick={async () => {
              if (!sel) return
              const s = await create.mutateAsync(sel)
              setOpen(false)
              setSel(null)
              void router.navigate({ to: '/sessions/$sessionId', params: { sessionId: s.id } })
            }}
          >
            {t('sessions.new')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
