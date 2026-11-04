import { Lock } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import type { Severity, Status } from '@/lib/api/types'
import { cn } from '@/lib/utils'

import { SEVERITY_META, STATUS_META } from '../constants'

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const meta = SEVERITY_META[severity]
  return (
    <Badge variant="outline" className={cn(meta.className, className)} title={meta.description}>
      {meta.label}
    </Badge>
  )
}

export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  const meta = STATUS_META[status]
  return (
    <Badge variant="outline" className={cn(meta.className, className)}>
      <span className={cn('size-1.5 rounded-full', meta.dot)} aria-hidden />
      {meta.label}
    </Badge>
  )
}

export function ConfidentialBadge() {
  return (
    <Badge
      variant="outline"
      className="text-muted-foreground border-dashed"
      title="Visible to reporter and triagers only"
    >
      <Lock aria-hidden />
      Confidential
    </Badge>
  )
}
