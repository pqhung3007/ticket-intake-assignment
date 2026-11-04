import { ArrowDown, Bot, Database, Globe, ShieldCheck, User } from 'lucide-react'

import { cn } from '@/lib/utils'

function Box({
  icon: Icon,
  title,
  lines,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  lines: string[]
  className?: string
}) {
  return (
    <div className={cn('bg-card rounded-lg border p-3 shadow-xs', className)}>
      <div className="flex items-center gap-2 text-sm font-medium">
        <Icon className="text-muted-foreground size-4" />
        {title}
      </div>
      <ul className="text-muted-foreground mt-1.5 space-y-0.5 text-xs">
        {lines.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
    </div>
  )
}

function Down({ label }: { label: string }) {
  return (
    <div className="text-muted-foreground flex items-center justify-center gap-2 py-2 text-xs">
      <ArrowDown className="size-4" aria-hidden />
      {label}
    </div>
  )
}

/** Request paths into the app. Both converge on the same service and policy. */
export function ArchitectureDiagram() {
  return (
    <figure aria-label="System architecture" className="space-y-0">
      <div className="grid gap-3 sm:grid-cols-2">
        <Box icon={User} title="Workspace member" lines={['Browser, signed in to N0', 'Uses this web UI']} />
        <Box
          icon={Bot}
          title="Bug Intake agent"
          lines={['Turns a chat message into a ticket', 'Calls create_ticket / list_tickets']}
        />
      </div>
      <Down label="HTTPS · platform-signed token (agent calls carry the invoking user + agent id)" />
      <Box
        icon={Globe}
        title="N0 platform"
        lines={['Workspace sign-in, app subdomain', 'Connector maps tools → REST endpoints']}
      />
      <Down label="same REST API for UI and tools: /api/v1/*" />
      <div className="rounded-xl border-2 border-dashed p-3">
        <p className="text-muted-foreground mb-2 text-xs font-medium">ticket-intake container (FastAPI)</p>
        <div className="grid gap-3 sm:grid-cols-3">
          <Box
            icon={ShieldCheck}
            title="auth"
            lines={['Verify JWT (JWKS)', 'Resolve role: member / triager / admin']}
          />
          <Box
            icon={ShieldCheck}
            title="tickets"
            lines={['router → service → repository', 'policy.py: one set of rules']}
          />
          <Box icon={ShieldCheck} title="users" lines={['Member directory', 'Triager grants (admin only)']} />
        </div>
      </div>
      <Down label="SQLAlchemy (async) · migrations on boot under an advisory lock" />
      <Box
        icon={Database}
        title="App Data (PostgreSQL, isolated schema)"
        lines={['tickets · ticket_events (append-only audit) · users · app_roles']}
      />
    </figure>
  )
}
