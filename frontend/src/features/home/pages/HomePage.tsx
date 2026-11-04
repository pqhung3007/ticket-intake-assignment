import { Plus, Users } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { useCurrentUser } from '@/features/auth'
import { StatsCards, TicketPanel } from '@/features/tickets'
import type { Me } from '@/lib/api/types'

/** The landing page differs by role: reporters track their bugs, triagers work a queue, admins oversee. */
export function HomePage() {
  const { data: me } = useCurrentUser()
  if (!me) return null
  if (me.role === 'admin') return <AdminHome me={me} />
  if (me.role === 'triager') return <TriagerHome me={me} />
  return <MemberHome me={me} />
}

const firstName = (me: Me) => (me.name ?? me.email ?? 'there').split(/[\s@]/)[0]

function ReportButton() {
  return (
    <Button asChild>
      <Link to="/tickets/new">
        <Plus aria-hidden />
        Report a bug
      </Link>
    </Button>
  )
}

/** Status cards on a dashboard jump to the full list filtered by that status. */
function StatusOverview() {
  const navigate = useNavigate()
  return (
    <StatsCards onSelect={(status) => void navigate(status ? `/tickets?status=${status}` : '/tickets')} />
  )
}

function MemberHome({ me }: { me: Me }) {
  return (
    <div className="space-y-6">
      <PageHeader
        title={`Hi ${firstName(me)}`}
        description="Track the bugs you reported and see what the team is working on."
        actions={<ReportButton />}
      />
      <TicketPanel
        title="Your reports"
        filters={{ scope: 'mine' }}
        empty="You haven't reported any bugs yet"
        limit={8}
      />
      <TicketPanel title="Recently reported" filters={{}} empty="No bugs reported yet" />
    </div>
  )
}

function TriagerHome({ me }: { me: Me }) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Triage queue"
        description={`${firstName(me)}, here is what needs your attention.`}
        actions={<ReportButton />}
      />
      <StatusOverview />
      <div className="grid gap-6 xl:grid-cols-2">
        <TicketPanel
          title="Needs triage"
          description="Open and not yet assigned"
          filters={{ scope: 'unassigned', status: 'open' }}
          empty="Nothing waiting for triage"
        />
        <TicketPanel
          title="Assigned to you"
          filters={{ scope: 'assigned' }}
          empty="No tickets are assigned to you"
        />
      </div>
    </div>
  )
}

function AdminHome({ me }: { me: Me }) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Workspace overview"
        description={`${firstName(me)}, here is how the workspace is doing.`}
        actions={
          <>
            <Button asChild variant="outline">
              <Link to="/admin/roles">
                <Users aria-hidden />
                Manage members
              </Link>
            </Button>
            <ReportButton />
          </>
        }
      />
      <StatusOverview />
      <div className="grid gap-6 xl:grid-cols-2">
        <TicketPanel
          title="Critical and open"
          filters={{ severity: 'critical', status: 'open' }}
          empty="No open critical bugs"
        />
        <TicketPanel
          title="Needs triage"
          description="Open and not yet assigned"
          filters={{ scope: 'unassigned', status: 'open' }}
          empty="Nothing waiting for triage"
        />
      </div>
    </div>
  )
}
