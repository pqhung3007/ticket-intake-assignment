import { Navigate, useLocation } from 'react-router'

import { Skeleton } from '@/components/ui/skeleton'

import { useCurrentUser } from '../api/queries'

/**
 * Sends signed-out visitors to the login screen and brings them back afterwards. A convenience
 * only: the API rejects unauthenticated calls itself.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { data: me, isPending, isError, error } = useCurrentUser()
  const location = useLocation()

  if (isPending) {
    return (
      <div className="space-y-4 p-8" aria-busy>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }
  if (isError) throw error // shown by the route error boundary
  if (!me) {
    const next = location.pathname + location.search
    return <Navigate to={next === '/' ? '/login' : `/login?next=${encodeURIComponent(next)}`} replace />
  }
  return <>{children}</>
}
