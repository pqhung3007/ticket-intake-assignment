import { ArrowRight, Inbox } from 'lucide-react'
import { Link } from 'react-router'

import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { Card, CardAction, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

import { useTicketList } from '../api/queries'
import type { TicketListFilters } from '../hooks/useTicketFilters'
import { TicketTable } from './TicketTable'

/** A short, pre-filtered list for dashboards, with a link to the full list under the same filters. */
export function TicketPanel({
  title,
  description,
  filters,
  empty,
  limit = 5,
}: {
  title: string
  description?: string
  filters: TicketListFilters
  empty: string
  limit?: number
}) {
  const list = useTicketList(filters)
  const tickets = list.data?.pages.flatMap((p) => p.items).slice(0, limit) ?? []
  const query = new URLSearchParams(
    Object.entries(filters).filter((e): e is [string, string] => e[1] !== undefined),
  ).toString()

  return (
    <Card className="gap-0 py-0">
      <CardHeader className="border-b py-4">
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        <CardAction>
          <Link
            to={query ? `/tickets?${query}` : '/tickets'}
            className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-sm"
          >
            View all <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </CardAction>
      </CardHeader>
      {list.isError ? (
        <div className="p-4">
          <ErrorState error={list.error} onRetry={() => void list.refetch()} />
        </div>
      ) : list.isPending ? (
        <div className="space-y-3 p-4" aria-busy>
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : tickets.length === 0 ? (
        <div className="p-4">
          <EmptyState icon={Inbox} title={empty} />
        </div>
      ) : (
        <TicketTable tickets={tickets} />
      )}
    </Card>
  )
}
