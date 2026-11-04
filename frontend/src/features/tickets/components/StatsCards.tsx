import { Skeleton } from '@/components/ui/skeleton'
import type { Status } from '@/lib/api/types'
import { cn } from '@/lib/utils'

import { useTicketStats } from '../api/queries'
import { STATUS_META, STATUSES } from '../constants'

/** Status counts that double as a status filter. */
export function StatsCards({
  active,
  onSelect,
}: {
  active?: Status
  onSelect: (s: Status | undefined) => void
}) {
  const stats = useTicketStats()

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {STATUSES.map((status) => {
        const meta = STATUS_META[status]
        const selected = active === status
        return (
          <button
            key={status}
            type="button"
            onClick={() => onSelect(selected ? undefined : status)}
            aria-pressed={selected}
            className={cn(
              'bg-card hover:bg-accent/50 flex flex-col gap-1 rounded-xl border p-4 text-left shadow-xs transition-colors',
              'focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:outline-none',
              selected && 'border-foreground/30 bg-accent/60',
            )}
          >
            <span className="text-muted-foreground flex items-center gap-2 text-sm">
              <span className={cn('size-2 rounded-full', meta.dot)} aria-hidden />
              {meta.label}
            </span>
            {stats.isPending ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <span className="text-2xl font-semibold tabular-nums">
                {stats.data?.by_status[status] ?? '–'}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
