import { ArrowRight, CircleDot, MessageSquare, Pencil, UserRound } from 'lucide-react'

import { PersonChip } from '@/components/common/PersonChip'
import type { Severity, Status, TicketEvent } from '@/lib/api/types'
import { formatDateTime, timeAgo } from '@/lib/utils'

import { FIELD_LABELS } from '../constants'
import { SeverityBadge, StatusBadge } from './Badges'

type Change = { from: unknown; to: unknown }
type Assignee = { id: string | null; name: string | null } | null

const ICONS = {
  created: CircleDot,
  updated: Pencil,
  status_changed: ArrowRight,
  assigned: UserRound,
  comment: MessageSquare,
} as const

function describe(event: TicketEvent): React.ReactNode {
  switch (event.type) {
    case 'created':
      return 'filed this ticket'
    case 'status_changed': {
      const d = event.data as { from: Status; to: Status }
      return (
        <span className="inline-flex flex-wrap items-center gap-1.5">
          moved it from <StatusBadge status={d.from} /> to <StatusBadge status={d.to} />
        </span>
      )
    }
    case 'assigned': {
      const d = event.data as { to: Assignee }
      return d.to?.id ? `assigned it to ${d.to.name ?? 'someone'}` : 'removed the assignee'
    }
    case 'updated': {
      const changes = (event.data as { changes?: Record<string, Change> }).changes ?? {}
      const sev = changes.severity
      const others = Object.keys(changes).filter((f) => f !== 'severity')
      return (
        <span className="inline-flex flex-wrap items-center gap-1.5">
          {sev && (
            <>
              changed severity <SeverityBadge severity={sev.from as Severity} />
              <ArrowRight className="size-3" aria-hidden />
              <SeverityBadge severity={sev.to as Severity} />
            </>
          )}
          {sev && others.length > 0 && 'and'}
          {others.length > 0 && `edited the ${others.map((f) => FIELD_LABELS[f] ?? f).join(', ')}`}
        </span>
      )
    }
    case 'comment':
      return 'commented'
  }
}

export function ActivityTimeline({ events }: { events: TicketEvent[] }) {
  return (
    <ol className="relative space-y-5 border-l pl-6">
      {events.map((event) => {
        const Icon = ICONS[event.type]
        return (
          <li key={event.id} className="relative">
            <span className="bg-background absolute top-0.5 -left-[33px] flex size-5 items-center justify-center rounded-full border">
              <Icon className="text-muted-foreground size-3" aria-hidden />
            </span>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
              <PersonChip
                name={event.actor.name}
                email={event.actor.email}
                agent={event.actor.agent}
                className="font-medium"
              />
              <span className="text-muted-foreground">{describe(event)}</span>
              <time
                className="text-muted-foreground text-xs"
                dateTime={event.created_at}
                title={formatDateTime(event.created_at)}
              >
                {timeAgo(event.created_at)}
              </time>
            </div>
            {event.type === 'comment' && event.body && (
              <div className="bg-muted/30 mt-2 rounded-lg border px-3 py-2 text-sm whitespace-pre-wrap">
                {event.body}
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
