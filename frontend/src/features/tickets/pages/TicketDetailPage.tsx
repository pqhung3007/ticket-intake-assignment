import { ArrowLeft, FileQuestion } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/lib/api/errors'
import type { Ticket } from '@/lib/api/types'

import { useTicket } from '../api/queries'
import { ActivityTimeline } from '../components/ActivityTimeline'
import { ConfidentialBadge, SeverityBadge, StatusBadge } from '../components/Badges'
import { CommentForm } from '../components/CommentForm'
import { EditTicketDialog } from '../components/EditTicketDialog'
import { TicketProperties } from '../components/TicketProperties'

export function TicketDetailPage() {
  const raw = useParams().number ?? ''
  const number = Number(raw)
  const query = useTicket(number)

  if (
    !Number.isInteger(number) ||
    number < 1 ||
    (query.error instanceof ApiError && query.error.status === 404)
  ) {
    return (
      <EmptyState
        icon={FileQuestion}
        title={`Ticket #${raw} not found`}
        description="It may not exist, or it may be confidential."
        action={
          <Button asChild variant="outline" size="sm">
            <Link to="/tickets">Back to tickets</Link>
          </Button>
        }
      />
    )
  }
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  if (query.isPending) return <DetailSkeleton />

  const { ticket, events, permissions } = query.data
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Link
          to="/tickets"
          className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-sm"
        >
          <ArrowLeft className="size-4" aria-hidden /> Tickets
        </Link>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight break-words">
              <span className="text-muted-foreground mr-2 font-mono">#{ticket.number}</span>
              {ticket.title}
            </h1>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={ticket.status} />
              <SeverityBadge severity={ticket.severity} />
              {ticket.confidential && <ConfidentialBadge />}
            </div>
          </div>
          {permissions.can_edit && <EditTicketDialog ticket={ticket} />}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <TicketBody ticket={ticket} />
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Activity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <ActivityTimeline events={events} />
              {permissions.can_comment && <CommentForm number={ticket.number} />}
            </CardContent>
          </Card>
        </div>
        <aside>
          <TicketProperties ticket={ticket} permissions={permissions} />
        </aside>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-1.5">
      <h2 className="text-muted-foreground text-xs font-medium tracking-wide uppercase">{title}</h2>
      <div className="text-sm leading-relaxed whitespace-pre-wrap">{children}</div>
    </section>
  )
}

function TicketBody({ ticket }: { ticket: Ticket }) {
  const empty =
    !ticket.description &&
    !ticket.steps_to_reproduce &&
    !ticket.expected_behavior &&
    !ticket.actual_behavior &&
    !ticket.environment
  return (
    <Card>
      <CardContent className="space-y-5">
        {empty && <p className="text-muted-foreground text-sm">No description provided.</p>}
        {ticket.description && <Section title="Description">{ticket.description}</Section>}
        {ticket.steps_to_reproduce && (
          <Section title="Steps to reproduce">{ticket.steps_to_reproduce}</Section>
        )}
        {(ticket.expected_behavior || ticket.actual_behavior) && (
          <div className="grid gap-5 sm:grid-cols-2">
            {ticket.expected_behavior && <Section title="Expected">{ticket.expected_behavior}</Section>}
            {ticket.actual_behavior && <Section title="Actual">{ticket.actual_behavior}</Section>}
          </div>
        )}
        {ticket.environment && <Section title="Environment">{ticket.environment}</Section>}
      </CardContent>
    </Card>
  )
}

function DetailSkeleton() {
  return (
    <div className="space-y-6" aria-busy>
      <Skeleton className="h-8 w-2/3" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Skeleton className="h-64" />
        <Skeleton className="h-80" />
      </div>
    </div>
  )
}
