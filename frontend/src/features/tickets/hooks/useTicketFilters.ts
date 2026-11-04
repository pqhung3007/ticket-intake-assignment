import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'

import type { Severity, Status } from '@/lib/api/types'

import { SEVERITIES, STATUSES } from '../constants'

export type Scope = 'all' | 'mine' | 'assigned' | 'unassigned'
const SCOPES: readonly Scope[] = ['all', 'mine', 'assigned', 'unassigned']

export interface TicketListFilters {
  status?: Status
  severity?: Severity
  scope?: Scope
  q?: string
}

function pick<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return value && (allowed as readonly string[]).includes(value) ? (value as T) : undefined
}

/** Filters live in the URL, so a filtered view can be bookmarked and shared. */
export function useTicketFilters() {
  const [params, setParams] = useSearchParams()

  const filters = useMemo<TicketListFilters>(
    () => ({
      status: pick(params.get('status'), STATUSES),
      severity: pick(params.get('severity'), SEVERITIES),
      scope: pick(params.get('scope'), SCOPES),
      q: params.get('q')?.trim() || undefined,
    }),
    [params],
  )

  const setFilter = useCallback(
    <K extends keyof TicketListFilters>(key: K, value: TicketListFilters[K] | undefined) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (value === undefined || value === '' || value === 'all') next.delete(key)
          else next.set(key, String(value))
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const reset = useCallback(() => setParams({}, { replace: true }), [setParams])
  const active = Object.values(filters).some((v) => v !== undefined)

  return { filters, setFilter, reset, active }
}
