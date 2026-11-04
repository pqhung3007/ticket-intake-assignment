import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import { ArchitectureDiagram } from '../components/ArchitectureDiagram'
import { PermissionMatrix } from '../components/PermissionMatrix'

const PRINCIPLES = [
  {
    title: 'Identity comes only from the platform',
    body: 'Every request carries a token signed by N0. The app verifies it against the issuer’s published keys and never reads identity from request bodies or unsigned headers.',
  },
  {
    title: 'Agents act as the user, with less power',
    body: 'An agent call is attributed to the person who invoked it, and the agent id is recorded on the ticket. Agents can only list, read and create, even if the user is a triager.',
  },
  {
    title: 'One set of rules for every entry point',
    body: 'The web UI and agent tools hit the same endpoints, and every permission check lives in one pure policy module with its own tests.',
  },
  {
    title: 'Safe to retry, safe to restart',
    body: 'create_ticket is idempotent (request_key, plus a retry window for keyless calls); edits use optimistic concurrency; migrations run on boot under a lock; the app keeps no state in memory.',
  },
]

export function AboutPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="How this app works" description="Architecture, identity and access rules." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Architecture</CardTitle>
            <CardDescription>Two ways in, one service, one set of rules.</CardDescription>
          </CardHeader>
          <CardContent>
            <ArchitectureDiagram />
          </CardContent>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Principles</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {PRINCIPLES.map((p) => (
                <div key={p.title} className="space-y-1">
                  <p className="text-sm font-medium">{p.title}</p>
                  <p className="text-muted-foreground text-sm">{p.body}</p>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="gap-2">
            <CardHeader>
              <CardTitle>Who can do what</CardTitle>
              <CardDescription>
                Enforced by the API. The UI only hides what you can&apos;t use.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PermissionMatrix />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
