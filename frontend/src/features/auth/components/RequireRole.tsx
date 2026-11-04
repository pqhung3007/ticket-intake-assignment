import { ShieldOff } from 'lucide-react'

import { EmptyState } from '@/components/common/EmptyState'
import type { Role } from '@/lib/api/types'

import { useCurrentUser } from '../api/queries'

const RANK: Record<Role, number> = { member: 0, triager: 1, admin: 2 }

/**
 * Hides UI the user cannot use. This is a convenience only: the API enforces every rule
 * itself, so a user who bypasses this still gets 403 from the server.
 */
export function RequireRole({ role, children }: { role: Role; children: React.ReactNode }) {
  const { data: me, isPending } = useCurrentUser()
  if (isPending) return null
  if (!me || RANK[me.role] < RANK[role]) {
    return (
      <EmptyState
        icon={ShieldOff}
        title="You don't have access to this page"
        description={`This page needs the ${role} role. Ask a workspace admin if you think you should have it.`}
      />
    )
  }
  return <>{children}</>
}
