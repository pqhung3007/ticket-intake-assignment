import { AlertTriangle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { errorMessage } from '@/lib/api/errors'

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="border-destructive/30 bg-destructive/5 flex flex-col items-center gap-3 rounded-lg border px-6 py-10 text-center"
    >
      <AlertTriangle className="text-destructive size-6" aria-hidden />
      <div className="space-y-1">
        <p className="font-medium">Couldn&apos;t load this</p>
        <p className="text-muted-foreground text-sm">{errorMessage(error)}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
