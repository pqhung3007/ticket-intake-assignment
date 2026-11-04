import { Bug, Loader2, Plus, SearchX } from 'lucide-react'
import { Link } from 'react-router'

import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

import { useTicketList } from '../api/queries'
import { StatsCards } from '../components/StatsCards'
import { TicketFilters } from '../components/TicketFilters'
import { TicketTable } from '../components/TicketTable'
import { useTicketFilters } from '../hooks/useTicketFilters'

export function TicketListPage() {
  const { filters, setFilter, reset, active } = useTicketFilters()
  const list = useTicketList(filters)
  const tickets = list.data?.pages.flatMap((p) => p.items) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tickets"
        description="Bugs reported by workspace members and their agents."
        actions={
          <Button asChild>
            <Link to="/tickets/new">
              <Plus aria-hidden />
              Report a bug
            </Link>
          </Button>
        }
      />

      <StatsCards active={filters.status} onSelect={(s) => setFilter('status', s)} />

      <Card className="gap-0 py-0">
        <div className="border-b p-4">
          <TicketFilters filters={filters} onChange={setFilter} onReset={reset} active={active} />
        </div>
        {list.isError ? (
          <div className="p-4">
            <ErrorState error={list.error} onRetry={() => void list.refetch()} />
          </div>
        ) : list.isPending ? (
          <div className="space-y-3 p-4" aria-busy>
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : tickets.length === 0 ? (
          <div className="p-4">
            {active ? (
              <EmptyState
                icon={SearchX}
                title="No tickets match these filters"
                action={
                  <Button variant="outline" size="sm" onClick={reset}>
                    Clear filters
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={Bug}
                title="No bugs reported yet"
                description="Report one here, or ask the Bug Intake agent in any channel."
                action={
                  <Button asChild size="sm">
                    <Link to="/tickets/new">Report a bug</Link>
                  </Button>
                }
              />
            )}
          </div>
        ) : (
          <div className={list.isPlaceholderData ? 'opacity-60 transition-opacity' : undefined}>
            <TicketTable tickets={tickets} />
            {list.hasNextPage && (
              <div className="flex justify-center border-t p-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => void list.fetchNextPage()}
                  disabled={list.isFetchingNextPage}
                >
                  {list.isFetchingNextPage && <Loader2 className="animate-spin" aria-hidden />}
                  Load more
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
