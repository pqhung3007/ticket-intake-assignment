import { Bot } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { PersonChip } from '@/components/common/PersonChip'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { TicketSummary } from '@/lib/api/types'
import { formatDateTime, timeAgo } from '@/lib/utils'

import { ConfidentialBadge, SeverityBadge, StatusBadge } from './Badges'

export function TicketTable({ tickets }: { tickets: TicketSummary[] }) {
  return (
    <>
      <TicketCardList tickets={tickets} />
      <div className="hidden md:block">
        <TicketDataTable tickets={tickets} />
      </div>
    </>
  )
}

/** Small screens: a stacked list, one card per ticket. */
function TicketCardList({ tickets }: { tickets: TicketSummary[] }) {
  return (
    <ul className="divide-y md:hidden">
      {tickets.map((t) => (
        <li key={t.id}>
          <Link
            to={`/tickets/${t.number}`}
            className="hover:bg-muted/50 focus-visible:bg-muted/50 flex flex-col gap-2 p-4 transition-colors focus-visible:outline-none"
          >
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground font-mono text-sm tabular-nums">#{t.number}</span>
              <span className="min-w-0 flex-1 font-medium break-words">{t.title}</span>
            </div>
            <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-xs">
              <StatusBadge status={t.status} />
              <SeverityBadge severity={t.severity} />
              <span className="bg-muted rounded px-1.5 py-0.5 font-mono">{t.target_app}</span>
              {t.created_via === 'agent' && (
                <span className="inline-flex items-center gap-1">
                  <Bot className="size-3" aria-hidden /> agent
                </span>
              )}
              {t.confidential && <ConfidentialBadge />}
              <span className="ml-auto">{timeAgo(t.updated_at)}</span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}

function TicketDataTable({ tickets }: { tickets: TicketSummary[] }) {
  const navigate = useNavigate()
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16 pl-4">#</TableHead>
          <TableHead>Title</TableHead>
          <TableHead className="w-28">Severity</TableHead>
          <TableHead className="w-32">Status</TableHead>
          <TableHead className="hidden w-44 lg:table-cell">Reporter</TableHead>
          <TableHead className="hidden w-44 xl:table-cell">Assignee</TableHead>
          <TableHead className="hidden w-32 pr-4 md:table-cell">Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tickets.map((t) => (
          <TableRow
            key={t.id}
            className="cursor-pointer"
            onClick={(e) => {
              // Let modified clicks (new tab) and real links behave natively.
              if (e.metaKey || e.ctrlKey || (e.target as HTMLElement).closest('a')) return
              void navigate(`/tickets/${t.number}`)
            }}
          >
            <TableCell className="text-muted-foreground pl-4 font-mono tabular-nums">{t.number}</TableCell>
            <TableCell className="max-w-0 whitespace-normal">
              <div className="flex min-w-0 flex-col gap-1">
                <Link
                  to={`/tickets/${t.number}`}
                  className="truncate font-medium hover:underline focus-visible:underline focus-visible:outline-none"
                >
                  {t.title}
                </Link>
                <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-xs">
                  <span className="bg-muted rounded px-1.5 py-0.5 font-mono">{t.target_app}</span>
                  {t.created_via === 'agent' && (
                    <span className="inline-flex items-center gap-1" title="Filed by an agent">
                      <Bot className="size-3" aria-hidden /> agent
                    </span>
                  )}
                  {t.confidential && <ConfidentialBadge />}
                </div>
              </div>
            </TableCell>
            <TableCell>
              <SeverityBadge severity={t.severity} />
            </TableCell>
            <TableCell>
              <StatusBadge status={t.status} />
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <PersonChip name={t.reporter.name} email={t.reporter.email} />
            </TableCell>
            <TableCell className="hidden xl:table-cell">
              {t.assignee ? (
                <PersonChip name={t.assignee.name} email={t.assignee.email} />
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell
              className="text-muted-foreground hidden pr-4 md:table-cell"
              title={formatDateTime(t.updated_at)}
            >
              {timeAgo(t.updated_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
