import { AlertTriangle } from 'lucide-react'
import { isRouteErrorResponse, Link, useRouteError } from 'react-router'

import { Button } from '@/components/ui/button'

/** Last-resort boundary for render errors and unknown routes. */
export function RouteErrorBoundary() {
  const error = useRouteError()
  const notFound = isRouteErrorResponse(error) && error.status === 404
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center">
      <AlertTriangle className="text-muted-foreground size-8" aria-hidden />
      <div className="space-y-1">
        <h1 className="text-xl font-semibold">{notFound ? 'Page not found' : 'Something went wrong'}</h1>
        <p className="text-muted-foreground text-sm">
          {notFound
            ? 'The page you are looking for does not exist.'
            : 'Reload the page or go back to tickets.'}
        </p>
      </div>
      <Button asChild variant="outline">
        <Link to="/tickets">Go to tickets</Link>
      </Button>
    </div>
  )
}
