import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Severity } from '@/lib/api/types'

import { SEVERITIES, SEVERITY_META } from '../constants'
import type { Scope, TicketListFilters } from '../hooks/useTicketFilters'

const SCOPE_LABELS: Record<Scope, string> = {
  all: 'All tickets',
  mine: 'Reported by me',
  assigned: 'Assigned to me',
  unassigned: 'Unassigned',
}

export function TicketFilters({
  filters,
  onChange,
  onReset,
  active,
}: {
  filters: TicketListFilters
  onChange: <K extends keyof TicketListFilters>(key: K, value: TicketListFilters[K] | undefined) => void
  onReset: () => void
  active: boolean
}) {
  // Debounce search so typing doesn't fire a request per keystroke.
  const [search, setSearch] = useState(filters.q ?? '')
  useEffect(() => setSearch(filters.q ?? ''), [filters.q])
  useEffect(() => {
    const id = setTimeout(() => {
      if ((filters.q ?? '') !== search.trim()) onChange('q', search.trim() || undefined)
    }, 300)
    return () => clearTimeout(id)
  }, [search, filters.q, onChange])

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
      <div className="relative sm:w-72">
        <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" aria-hidden />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search title, description, app"
          className="pl-8"
          aria-label="Search tickets"
          maxLength={100}
        />
      </div>
      <Select value={filters.scope ?? 'all'} onValueChange={(v) => onChange('scope', v as Scope)}>
        <SelectTrigger className="sm:w-44" aria-label="Scope">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(Object.keys(SCOPE_LABELS) as Scope[]).map((s) => (
            <SelectItem key={s} value={s}>
              {SCOPE_LABELS[s]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={filters.severity ?? 'all'}
        onValueChange={(v) => onChange('severity', v === 'all' ? undefined : (v as Severity))}
      >
        <SelectTrigger className="sm:w-40" aria-label="Severity">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Any severity</SelectItem>
          {SEVERITIES.map((s) => (
            <SelectItem key={s} value={s}>
              {SEVERITY_META[s].label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {active && (
        <Button variant="ghost" size="sm" onClick={onReset}>
          <X aria-hidden />
          Clear filters
        </Button>
      )}
    </div>
  )
}
