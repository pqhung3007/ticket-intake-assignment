import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'

import type { TicketListFilters } from '../hooks/useTicketFilters'
import { ticketKeys } from './keys'

const PAGE_SIZE = 25

export function useTicketList(filters: TicketListFilters) {
  return useInfiniteQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: async ({ pageParam }) => {
      const { scope, ...rest } = filters
      return unwrap(
        await api.GET('/api/v1/tickets', {
          params: {
            query: {
              ...rest,
              reporter: scope === 'mine' ? 'me' : undefined,
              assignee: scope === 'assigned' ? 'me' : scope === 'unassigned' ? 'none' : undefined,
              limit: PAGE_SIZE,
              cursor: pageParam,
            },
          },
        }),
      )
    },
    initialPageParam: undefined as number | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    placeholderData: keepPreviousData,
  })
}

export function useTicketStats() {
  return useQuery({
    queryKey: ticketKeys.stats(),
    queryFn: async () => unwrap(await api.GET('/api/v1/tickets/stats')),
  })
}

export function useTicket(number: number) {
  return useQuery({
    queryKey: ticketKeys.detail(number),
    queryFn: async () => unwrap(await api.GET('/api/v1/tickets/{number}', { params: { path: { number } } })),
    enabled: Number.isInteger(number) && number > 0,
  })
}
