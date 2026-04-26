import * as React from 'react'
import { cn } from '@/lib/utils'

function Progress({ className, value, ...props }: React.ComponentProps<'div'> & { value?: number | null }) {
  return (
    <div className={cn('bg-secondary relative h-2 w-full overflow-hidden rounded-full', className)} {...props}>
      <div
        className="h-full w-full flex-1 bg-primary transition-all"
        style={{ transform: `translateX(-${100 - (value ?? 0)}%)` }}
      />
    </div>
  )
}

export { Progress }
