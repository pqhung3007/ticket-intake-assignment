import type { TicketListFilters } from '../hooks/useTicketFilters'

/** Query key factory: one place defines cache structure, so invalidation stays correct. */
export const ticketKeys = {
  all: ['tickets'] as const,
  lists: () => [...ticketKeys.all, 'list'] as const,
  list: (filters: TicketListFilters) => [...ticketKeys.lists(), filters] as const,
  stats: () => [...ticketKeys.all, 'stats'] as const,
  details: () => [...ticketKeys.all, 'detail'] as const,
  detail: (number: number) => [...ticketKeys.details(), number] as const,
}
