import { Bot, Lock } from 'lucide-react'
import { toast } from 'sonner'

import { PersonChip } from '@/components/common/PersonChip'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { useUsers } from '@/features/users'
import type { Status, Ticket, TicketPermissions } from '@/lib/api/types'
import { formatDateTime } from '@/lib/utils'

import { useUpdateTicket } from '../api/mutations'
import { STATUS_META } from '../constants'
import { SeverityBadge, StatusBadge } from './Badges'
import { handleMutationError } from './handleMutationError'

const UNASSIGNED = '__none__'

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[96px_1fr] items-center gap-3 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0">{children}</dd>
    </div>
  )
}

export function TicketProperties({
  ticket,
  permissions,
}: {
  ticket: Ticket
  permissions: TicketPermissions
}) {
  const update = useUpdateTicket(ticket.number)
  const users = useUsers('', { enabled: permissions.can_assign })

  const setStatus = (status: string) =>
    update.mutate(
      { version: ticket.version, status: status as Status },
      {
        onSuccess: (t) => toast.success(`Moved to ${STATUS_META[t.status].label}`),
        onError: handleMutationError,
      },
    )

  const setAssignee = (value: string) =>
    update.mutate(
      { version: ticket.version, assignee_id: value === UNASSIGNED ? null : value },
      {
        onSuccess: (t) =>
          toast.success(t.assignee ? `Assigned to ${t.assignee.name ?? 'user'}` : 'Unassigned'),
        onError: handleMutationError,
      },
    )

  const statusOptions = [ticket.status, ...permissions.allowed_statuses]

  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle className="text-sm">Details</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3">
          <Row label="Status">
            {permissions.allowed_statuses.length > 0 ? (
              <Select value={ticket.status} onValueChange={setStatus} disabled={update.isPending}>
                <SelectTrigger size="sm" className="w-full" aria-label="Status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {statusOptions.map((s) => (
                    <SelectItem key={s} value={s}>
                      {STATUS_META[s].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <StatusBadge status={ticket.status} />
            )}
          </Row>
          <Row label="Severity">
            <SeverityBadge severity={ticket.severity} />
          </Row>
          <Row label="Assignee">
            {permissions.can_assign ? (
              <Select
                value={ticket.assignee?.id ?? UNASSIGNED}
                onValueChange={setAssignee}
                disabled={update.isPending || users.isPending}
              >
                <SelectTrigger size="sm" className="w-full" aria-label="Assignee">
                  <SelectValue placeholder="Unassigned" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                  {ticket.assignee && !users.data?.items.some((u) => u.id === ticket.assignee?.id) && (
                    <SelectItem value={ticket.assignee.id}>
                      {ticket.assignee.name ?? ticket.assignee.id}
                    </SelectItem>
                  )}
                  {users.data?.items.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.name ?? u.email ?? u.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : ticket.assignee ? (
              <PersonChip name={ticket.assignee.name} email={ticket.assignee.email} />
            ) : (
              <span className="text-muted-foreground">Unassigned</span>
            )}
          </Row>
          <Row label="App">
            <span className="bg-muted rounded px-1.5 py-0.5 font-mono text-xs">{ticket.target_app}</span>
          </Row>
          <Separator />
          <Row label="Reporter">
            <PersonChip name={ticket.reporter.name} email={ticket.reporter.email} />
          </Row>
          <Row label="Filed via">
            <span className="inline-flex min-w-0 items-center gap-1.5">
              {ticket.created_via === 'agent' ? (
                <>
                  <Bot className="text-muted-foreground size-4 shrink-0" aria-hidden />
                  <span className="truncate" title={ticket.created_by_agent ?? undefined}>
                    Agent{ticket.created_by_agent ? ` · ${ticket.created_by_agent}` : ''}
                  </span>
                </>
              ) : (
                'Web form'
              )}
            </span>
          </Row>
          <Row label="Created">{formatDateTime(ticket.created_at)}</Row>
          <Row label="Updated">{formatDateTime(ticket.updated_at)}</Row>
          {ticket.resolved_at && <Row label="Resolved">{formatDateTime(ticket.resolved_at)}</Row>}
          {ticket.confidential && (
            <Row label="Visibility">
              <span className="inline-flex items-center gap-1.5">
                <Lock className="text-muted-foreground size-4" aria-hidden /> Reporter & triagers
              </span>
            </Row>
          )}
        </dl>
      </CardContent>
    </Card>
  )
}
